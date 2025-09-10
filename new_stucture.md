ProphitAI/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   └── controllers/
│   ├── services/
│   ├── repositories/
│   ├── models/
│   │   ├── requests/
│   │   ├── responses/
│   │   └── domain/
│   ├── domain/
│   │   ├── portfolio_optimization/
│   │   │   ├── phase_one/
│   │   │   └── phase_two/
│   │   ├── prophit_alts/
│   │   │   └── consumer_staples_fund/
│   │   │       ├── build_portfolio/
│   │   │       │   ├── cio/
│   │   │       │   ├── cro/
│   │   │       │   ├── industry_agents/
│   │   │       │   └── prompts/
│   │   │       │       └── industry_prompts/
│   │   │       └── manage_portfolio/
│   │   ├── prophit_gpt/
│   │   │   ├── dataRetrievalTools/
│   │   │   ├── functionSchemas/
│   │   │   └── placeOrders/
│   │   └── stress_test/
│   ├── db/
│   │   ├── core/
│   │   ├── jobs/
│   │   └── monitor/
│   ├── core/
│   ├── utils/
│   └── middleware/
├── core_libs/
│   ├── calculations/
│   │   ├── core/
│   │   ├── factors/
│   │   ├── performance/
│   │   ├── portfolio/
│   │   │   └── build/
│   │   ├── returns/
│   │   ├── risk/
│   │   ├── sectors/
│   │   └── technical/
│   └── agent_framework/
│       ├── agent_output/
│       └── base_agent/
│           ├── base_tools/
│           ├── core/
│           ├── events/
│           ├── memory/
│           │   └── memory_store/
│           │       └── semantic_memory/
│           │           └── consumer_staples_fund/
│           └── tasks/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── smoke/
└── scripts/