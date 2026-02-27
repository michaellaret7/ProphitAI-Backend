"""Portfolio data repository - organized into submodules by domain."""

from app.repositories.portfolio.retrieval import (
    _flatten_portfolio_to_legacy_format,
    retrieve_portfolio,
    retrieve_portfolios_batch,
    list_portfolios,
    get_all_portfolio_ids,
)

from app.repositories.portfolio.crud import (
    add_portfolio,
    update_portfolio,
    delete_portfolio,
    delete_portfolio_by_name,
)

from app.repositories.portfolio.preferences import (
    get_portfolio_preference,
    create_portfolio_preference,
    update_portfolio_preference,
    delete_portfolio_preference,
)

from app.repositories.portfolio.alerts import (
    get_portfolio_alert_state,
)
