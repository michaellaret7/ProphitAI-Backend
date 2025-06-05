**List of things to do**

Emoji references
    a. ✅ --> means task is done 
    b. ⏳--> in progress

1. *Push user portfolio to database*
    a. Retrieve the ibkr portfolio and push to the database ✅
    b. Build a function to retrieve the portfolio from the database ✅
    c. Build an update portfolio function (args: *user id or user name*) ✅
    d. Have the functions in phase_one_formatting.py get price data from the database ✅
    e. Change structure to be one schema (public) ✅
        i. Have there be 4 tables (final_portfolio, sector_allocations, portfolio_thesis, and user_information) ✅
        ii. Each one will have the user's username, the user's user id, the portfolio name, and the portfolio id ✅
        iii. Change the way backtest retrieves the positions from the portfolios✅

2. *Create Front End infrastructure*
    a. Create a front end folder (test on laptop first) ✅
    b. Install React 19 framework using vite ✅
    c. Create Landing page ✅
    d. Set Next meeting with Mo ✅

3. *Read and refine prompts*
    a. Print on iPad and edit by hand ✅
    b. Do this for phase_one ✅
    c. Do this for phase_two ✅
    d. Test to see how the new prompts perform ✅
    e. Get new investor profiles from dad for phase_two

4. *Build different types of portfolios (Long only, Long/Short)*
    a. Modify the prompts to include long/short availability 
    b. Have the user decide which to make long only or long/short 
    c. Once phase_one is properly doing long/short portfolios, alter phase_two to make find stocks to short as well as stocks to go long 
    e. Add crypto to the possible asset classes 
    f. Give heavier weights to certain sectors and more tickers to heavier sectors

5. *Write code documentation and rules in a .md file*
    a. Write documentation 
    b. Write a readme 

8. *Build Dashboard on frontend*
    a. Add performance graph and comparison ✅
    b. Map out what else should be on the dashboard page  
    c. Add alerts, news, etc.

9. *Build chatbot page*
    a. build first pass chatbot page for the frontend ✅
    b. build more tools for the gpt 
    c. make sure the graphics inside the chatbot are clean and work well

10. *Build optimization page*
    a. connect optimization to the front end 
    b. have cool graphics while user is waiting for the process
    c. let the user pick the model 
    d. once optimization is finished show backtest and metrics, etc.
    e. have the user be able to add and subtract tickers from the list 
    f. Have an implement button and the agent will place all the trades for the user 


Maintenance Items and Code optimization:
1. move functions to utils 
    a. Find functions to push to the utils folder 
2. turn file_structure into .md ✅
3. create rules for the program (naming conventions)
4. create consistency for folder and file names 
5. make a utils file to get the price data from the db, one function to get the data 
6. IN PHASE_TWO HAVE THE QUANTITATIVE FILTERS BE BASED ON THE USERS INVESTMENT PROFILE 
7. Break Down portfolioData.py
8. Get price data for tickers that do not have price data *this is important and needs to be done*
    a. After this go through the database and get rid of all of the tickers without price data
9. MAKE A VIRTUAL ENV FOR PROJ PYTHON 3.12.0 ✅
10. Review backend/api code structure and naming conventions 
    a. review the backend to front end pipleine 
    b. make sure its well structured, maintainable, and scaleable
11. Go through all backend code and give a 1-2 sentence blurb on what each function does and how it fits (VERY IMPORTANT NEED TO DO THIS ASAP)
12. Make the portfolio icons the same as the ones in the Dashboard


Important commands:
1. uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
2. .\.venv\Scripts\Activate.ps1

Important Sites for help:
1. GitDocify for building a ReadME --> https://gitdocify.com/
2. ReactBits for cool front end effects --> https://www.reactbits.dev/text-animations/split-text
