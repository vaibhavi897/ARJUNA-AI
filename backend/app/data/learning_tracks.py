"""Career-track metadata, subject taxonomy and topic prerequisites.

This is a *framework*, not content: topic names, a rough size in hours and the
prerequisite chain. Gemini turns it into an individual journey for each learner;
no notes, quizzes or schedules live here.

DSL: each subject is a chain "Topic F4 > Topic I5 > ..." where the letter is the
phase (F=foundation, I=intermediate, A=advanced) and the number is rough hours.
Each topic requires the previous one in its chain; ``deps`` adds cross-subject
prerequisites by title.
"""

PHASES = [
    {"key": "foundation", "title": "Foundation", "share": 0.30},
    {"key": "intermediate", "title": "Intermediate", "share": 0.30},
    {"key": "advanced", "title": "Advanced", "share": 0.20},
    {"key": "projects", "title": "Projects", "share": 0.15},
    {"key": "final", "title": "Final Assessment", "share": 0.05},
]

TRACKS = [
    dict(slug="software-development-engineer", title="Software Development Engineer", category="Technology", career="software-engineer",
         description="Build strong software engineering fundamentals: programming, data structures, algorithms, system design and professional practice.",
         subjects={
             "Programming": "Programming Basics F6 > Object-Oriented Design I8 > Functional and Concurrent Programming A8",
             "Data Structures": "Arrays and Strings F6 > Linked Lists, Stacks and Queues F6 > Trees and Graphs I10 > Heaps, Tries and Hashing I8",
             "Algorithms": "Complexity Analysis F4 > Sorting and Searching F6 > Recursion and Backtracking I8 > Dynamic Programming A12 > Graph Algorithms A10",
             "Systems": "Operating Systems Basics I6 > Computer Networks I6 > Databases and SQL I8 > System Design A14",
             "Engineering": "Git and Collaboration F3 > Testing and Debugging I6 > CI/CD and Deployment A6",
         }, deps={"Graph Algorithms": ["Trees and Graphs"], "Object-Oriented Design": ["Programming Basics"]}),
    dict(slug="backend-developer", title="Backend Developer", category="Technology", career="backend-developer",
         description="Design and build reliable server-side systems: APIs, databases, security, caching and scalable architecture.",
         subjects={
             "Language": "Python or Java Core F8 > Concurrency and Async I8",
             "Web and APIs": "HTTP and REST F5 > API Design I8 > Authentication and Authorisation I8 > GraphQL and gRPC A6",
             "Databases": "SQL Fundamentals F8 > Data Modelling I6 > Indexing and Query Optimisation I8 > NoSQL and Caching A8",
             "Architecture": "Layered Architecture I5 > Message Queues and Events A8 > Microservices A10 > Observability A6",
             "Delivery": "Git and Linux Basics F5 > Docker I6 > CI/CD and Cloud Deployment A8",
         }, deps={"API Design": ["Python or Java Core"], "Message Queues and Events": ["API Design"]}),
    dict(slug="frontend-developer", title="Frontend Developer", category="Technology", career="frontend-developer",
         description="Craft fast, accessible, maintainable user interfaces with modern web technologies.",
         subjects={
             "Web Fundamentals": "HTML and Semantics F5 > CSS Layout and Responsive Design F8 > JavaScript Core F10 > Browser APIs and DOM I6",
             "Frameworks": "TypeScript Basics I6 > React Fundamentals I10 > State Management I8 > Next.js and Rendering Strategies A8",
             "Quality": "Accessibility I5 > Testing Frontend Code I6 > Performance Optimisation A8",
             "Tooling": "Git and npm F3 > Build Tools and Bundling I4 > Design Systems A6",
         }, deps={"React Fundamentals": ["JavaScript Core"]}),
    dict(slug="full-stack-developer", title="Full Stack Developer", category="Technology", career="full-stack-developer",
         description="Own features end to end: UI, APIs, databases, deployment and testing.",
         subjects={
             "Frontend": "HTML, CSS and JavaScript F12 > React and TypeScript I12 > State and Data Fetching I6",
             "Backend": "A Server Language F8 > REST API Design I8 > Authentication I6",
             "Data": "SQL and Data Modelling F8 > ORMs and Migrations I6 > Caching and Search A6",
             "Delivery": "Git Workflow F3 > Docker and Deployment I8 > Testing End to End A8 > Monitoring A5",
         }, deps={"REST API Design": ["HTML, CSS and JavaScript"]}),
    dict(slug="data-analyst", title="Data Analyst", category="AI & Data", career="data-analyst",
         description="Turn raw data into insight: SQL, spreadsheets, statistics, visualisation and storytelling.",
         subjects={
             "SQL": "SQL Basics F8 > Joins and Aggregations F8 > Window Functions I8 > Query Performance A5",
             "Spreadsheets": "Excel Essentials F6 > Pivot Tables and Formulas I6",
             "Statistics": "Descriptive Statistics F8 > Probability Basics I8 > Hypothesis Testing I8 > A/B Testing A6",
             "Python": "Python for Data F8 > Pandas and Data Cleaning I10 > EDA Techniques I6",
             "Communication": "Data Visualisation Principles I6 > Dashboards with BI Tools I8 > Data Storytelling A5",
         }),
    dict(slug="data-scientist", title="Data Scientist", category="AI & Data", career="data-scientist",
         description="Build predictive models and decision tools using statistics and machine learning.",
         subjects={
             "Math": "Linear Algebra Essentials F8 > Calculus for ML F6 > Probability and Statistics I10 > Optimisation A6",
             "Programming": "Python and NumPy F8 > Pandas and Data Wrangling F8 > SQL for Analytics I6",
             "Machine Learning": "Supervised Learning I12 > Model Evaluation and Validation I8 > Feature Engineering I8 > Ensembles and Boosting A10 > Unsupervised Learning A8",
             "Applied": "Experiment Design I6 > Time Series A8 > Model Deployment Basics A6",
         }, deps={"Supervised Learning": ["Probability and Statistics", "Python and NumPy"]}),
    dict(slug="ml-engineer", title="ML Engineer", category="AI & Data", career="machine-learning-engineer",
         description="Take models into production: training pipelines, serving, monitoring and MLOps.",
         subjects={
             "ML Core": "Python for ML F8 > Classical ML I12 > Deep Learning Fundamentals I12 > Model Optimisation A8",
             "Engineering": "Software Engineering for ML I8 > Data Pipelines I8 > Docker and Kubernetes Basics A8",
             "MLOps": "Experiment Tracking I5 > Model Serving A8 > Monitoring and Drift A6 > CI/CD for ML A6",
             "Math": "Linear Algebra and Calculus F10 > Probability I8",
         }, deps={"Classical ML": ["Linear Algebra and Calculus"]}),
    dict(slug="ai-engineer", title="AI Engineer", category="AI & Data", career="ai-engineer",
         description="Build products on foundation models: prompting, retrieval, agents, evaluation and safety.",
         subjects={
             "Foundations": "Python and APIs F8 > ML and NLP Basics F10 > Transformers and LLMs I10",
             "Applied LLMs": "Prompt Engineering I6 > Embeddings and Vector Search I8 > Retrieval-Augmented Generation I10 > Agents and Tool Use A10",
             "Quality": "LLM Evaluation I6 > Safety and Guardrails A6 > Cost and Latency Optimisation A6",
             "Delivery": "Backend Services for AI I8 > Deployment and Monitoring A8",
         }),
    dict(slug="data-engineer", title="Data Engineer", category="AI & Data", career="data-engineer",
         description="Design reliable data pipelines, warehouses and platforms.",
         subjects={
             "Core": "SQL Mastery F10 > Python for Data Engineering F8 > Linux and Shell F4",
             "Modelling": "Data Warehousing Concepts I8 > Dimensional Modelling I8 > Data Lakes and Lakehouse A6",
             "Pipelines": "ETL and ELT Patterns I8 > Workflow Orchestration I8 > Batch Processing with Spark A10 > Streaming and Kafka A10",
             "Quality": "Data Quality and Testing I6 > Governance and Security A5 > Cloud Data Platforms A8",
         }),
    dict(slug="business-analyst", title="Business Analyst", category="Consulting", career="business-analyst",
         description="Bridge business and technology: requirements, process analysis, data and stakeholder management.",
         subjects={
             "Foundations": "Business Fundamentals F6 > Requirements Elicitation F6 > Process Mapping I6 > User Stories and Acceptance I5",
             "Data": "Excel and Data Analysis F8 > SQL for Analysts I8 > Dashboards and Reporting I6",
             "Delivery": "Agile and Scrum I5 > Stakeholder Management I5 > Business Cases and ROI A6",
         }),
    dict(slug="sql-developer", title="SQL Developer", category="Technology", career=None,
         description="Master relational databases: querying, modelling, performance and administration basics.",
         subjects={
             "Querying": "SQL Basics F8 > Joins and Subqueries F8 > Window Functions and CTEs I8 > Advanced Query Patterns A8",
             "Design": "Relational Modelling F6 > Normalisation I5 > Indexing Strategies I8 > Transactions and Concurrency A8",
             "Practice": "Stored Procedures and Functions I8 > Query Plans and Tuning A10 > Backup and Security Basics A5",
         }),
    dict(slug="python-developer", title="Python Developer", category="Technology", career=None,
         description="Write idiomatic, tested, production-ready Python across scripting, web and data.",
         subjects={
             "Language": "Python Syntax and Types F8 > Functions and Modules F6 > OOP in Python I8 > Iterators, Generators, Decorators I8 > Async and Concurrency A8",
             "Ecosystem": "Virtual Environments and Packaging F3 > Testing with pytest I6 > Type Hints and Linting I5",
             "Applications": "Working with Files and APIs I6 > Web Frameworks (FastAPI or Django) I10 > Databases and ORMs A8",
         }),
    dict(slug="investment-banking-analyst", title="Investment Banking Analyst", category="Finance", career="investment-banker",
         description="Prepare for banking analyst roles: accounting, valuation, modelling and deal execution.",
         subjects={
             "Accounting": "Three Financial Statements F8 > Accounting Adjustments I6 > Quality of Earnings A5",
             "Valuation": "Time Value of Money F4 > DCF Valuation I10 > Comparable Companies and Precedents I8 > LBO Basics A10",
             "Modelling": "Excel Modelling Best Practice F6 > Three-Statement Models I10 > M&A Accretion and Dilution A8",
             "Markets": "Capital Markets Overview F5 > IPO and Debt Raising Process I6 > Pitchbooks and Deal Execution A6",
         }),
    dict(slug="equity-research-analyst", title="Equity Research Analyst", category="Finance", career="equity-research-analyst",
         description="Analyse companies and sectors and write investment views.",
         subjects={
             "Foundations": "Financial Statement Analysis F8 > Ratio Analysis F6 > Industry and Competitive Analysis I6",
             "Valuation": "DCF and Relative Valuation I10 > Earnings Forecasting Models I8 > Target Price Construction A6",
             "Practice": "Reading Filings and Earnings Calls I5 > Writing Research Reports I6 > Sector Deep Dive A8",
         }),
    dict(slug="quantitative-analyst", title="Quantitative Analyst", category="Finance", career="quantitative-analyst",
         description="Apply mathematics, statistics and programming to pricing, trading and risk.",
         subjects={
             "Math": "Probability and Statistics F10 > Linear Algebra F6 > Stochastic Calculus I12 > Numerical Methods A8",
             "Finance": "Derivatives Basics I8 > Options Pricing Models I10 > Fixed Income and Risk Measures A8",
             "Programming": "Python for Quant F8 > C++ Essentials I10 > Backtesting and Strategy Research A10",
         }),
    dict(slug="financial-analyst", title="Financial Analyst", category="Finance", career="financial-analyst",
         description="Support business decisions with budgeting, forecasting and financial analysis.",
         subjects={
             "Core": "Accounting Fundamentals F8 > Financial Statement Analysis F8 > Corporate Finance Basics I8",
             "Planning": "Budgeting and Forecasting I8 > Variance Analysis I5 > Business Case Modelling A8",
             "Tools": "Advanced Excel F8 > SQL and Power BI I8 > Management Reporting A5",
         }),
    dict(slug="management-consultant", title="Management Consultant", category="Consulting", career="management-consultant",
         description="Structure and solve business problems with analysis and communication.",
         subjects={
             "Thinking": "Problem Structuring and Issue Trees F6 > Hypothesis-Driven Analysis I6 > Case Interview Frameworks I8",
             "Analysis": "Market Sizing F5 > Profitability and Cost Analysis I8 > Excel and Data Synthesis I8",
             "Communication": "Slide Storytelling I6 > Client Communication I5 > Final Case Practice A10",
         }),
    dict(slug="strategy-consultant", title="Strategy Consultant", category="Consulting", career="strategy-consultant",
         description="Advise on growth, market entry, M&A and portfolio strategy.",
         subjects={
             "Strategy": "Strategy Frameworks F6 > Competitive Analysis I6 > Market Entry and Growth Strategy A8",
             "Quant": "Market Sizing and Modelling F8 > Valuation Basics I8 > M&A Strategy A8",
             "Practice": "Industry Research Methods I5 > Executive Communication I5 > Strategy Case Practice A10",
         }),
    dict(slug="product-manager", title="Product Manager", category="Product", career="product-manager",
         description="Define what to build and why: discovery, prioritisation, metrics and execution.",
         subjects={
             "Discovery": "Product Fundamentals F5 > User Research F6 > Problem Framing I5 > Competitive Analysis I5",
             "Execution": "Writing PRDs and User Stories I6 > Prioritisation Frameworks I5 > Agile Delivery I5 > Working with Engineering A6",
             "Data": "Product Metrics F6 > SQL for PMs I8 > Experimentation and A/B Tests A8",
             "Strategy": "Roadmapping I6 > Go-to-Market A6 > Product Case Practice A8",
         }),
    dict(slug="cybersecurity-analyst", title="Cybersecurity Analyst", category="Security", career="cybersecurity-analyst",
         description="Detect, investigate and respond to threats; understand networks, systems and controls.",
         subjects={
             "Foundations": "Networking Fundamentals F8 > Operating Systems and Linux F8 > Security Principles F6",
             "Defence": "Threat Landscape and MITRE ATT&CK I6 > SIEM and Log Analysis I10 > Vulnerability Management I8 > Incident Response A10",
             "Offence": "Web Application Security I10 > Penetration Testing Basics A10",
             "Governance": "Cryptography Essentials I6 > Security Frameworks and Compliance A6 > Cloud Security A8",
         }),
]
