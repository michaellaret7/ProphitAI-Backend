Ok, this is a step in the right direction. Now, this is what we will do. I will give/show you the kind of workflow I want the agent to be running and then you will edit the agent workflow analysis file to reflect this approach. You will replace the current new solution in the workflow analysis file with my solution. 

Here is my desired workflow for the Agent. Our aim is to build a highly thinking, observing, and reasoning agent that is still staying within the guidelines and completing hard tasks. 
EXAMPLE OF DESIRED WORKFLOW -->
User request: "Find me 3 stocks in the energy sector with strong and growing fundamentals with strong momentum"
---------------------------------------------------------------------------------------------------------------------
Main Task 1: Call Stock Screener Tool for energy companies 
    {"Thinking": Ok, the user wants to screen/pick momentum stocks with strong and growing fundamentals, I will run the stock screener tool 3-5 times with criteria XYZ"} --> Agent thinking through problem (NO TOOL CALL)
        ✓ stock screener Tool Call -- success:true
        ✓ stock screener Tool Call -- success:true
        ✓ stock screener Tool Call -- success:true
        ✓ stock screener Tool Call -- success:true
    {"Observations": Stock XYZ had some really good momentum numbers and strong roic, Stock ABB had really poor momentum and growth prospect etc.}
    {"Reasoning": So far I really like stock XYZ, we need more data and the plan is not finished but I will continue to the next task}
        ✓ Advance to next main task Tool Call -- success:true --> the agent is the one who controls when to move on the to next task and has tools to do so

Main Task 2: Query fundamental and technical data for the tickers 
    Subtask 2a: 
        {thinking}
        {tool useage for data, however many the agent wants}
        {observation}
        {reasoning}
        ✓ Advance to next sub task Tool Call -- success:true
    Subtask 2b:
        {thinking}
        {tool useage for data, however many the agent wants}
        {observation}
        {reasoning}
        ✓ Advance to next sub task Tool Call -- success:true
    
    {"Reasoning": Ok I got all the data I needed from the subtasks, etc. lets go to the next main task}
    ✓ Advance to next main task Tool Call -- success:true



Great Work, Now our next step is implementation. The Goal is to build a new base agent with the desired workflow we discussed (refer to the AGENT_WORKFLOW_ANALYSIS.md file). I create a base_agent_v2 folder in the agentic framework folder and this is where the new code will go. Your task is to build a comprehenxive plan and checklist for accomplishing our goal. This plan will go in an md file in the claude folder.
The following is the order of operations we will conduct this refactoring:
1. Determine which files, classes, and pieces of the current base agent we will be using. (We dont want to start from scratch here. We want to copy the best pieces of the current agent and carry them over into our new agent with a new workflow)
2. Determine the file architecture/structure of the base_agent_v2 folder
3. come up with a list of new tools that new need to build and implement 
4. come up with a full comprehensive plan that is broken down into phases broken into very detailed and explanatory todo items with examples and instrcutions on how to complete the todo list item