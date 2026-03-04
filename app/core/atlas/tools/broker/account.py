from app.core.atlas.tools.decorator import agent_tool
from app.core.atlas.tools.responses import success_response, error_response
from app.brokers.snaptrade.broker import SnapTradeBroker
from app.brokers.snaptrade.models.account import AccountInfo
from app.repositories.user.broker import resolve_snaptrade_credentials
from concurrent.futures import ThreadPoolExecutor


@agent_tool(name="account_info")
def account_info(
    email: str,
) -> str:
    """
    Get the account information for the given email.
    """
    try:
        user = resolve_snaptrade_credentials(email=email)
        snaptrade_broker = SnapTradeBroker()

        args = dict(
            user_id=user["snaptrade_user_id"],
            user_secret=user["snaptrade_user_secret"],
            account_id=user["snaptrade_account_id"],
        )

        with ThreadPoolExecutor() as pool:
            details_future = pool.submit(snaptrade_broker.accounts.get_account_details, **args)
            balances_future = pool.submit(snaptrade_broker.accounts.get_balances, **args)

        details = details_future.result()
        balances = balances_future.result()

        account = AccountInfo.from_raw(details, balances)
        return success_response(account.model_dump())
    except Exception as e:
        return error_response(f"Failed to get account info for {email}: {str(e)}")
