"""Shared registry, industry defaults and the career() authoring helper.

Everything authored here is *qualitative* (descriptions, workflows, titles,
well-known employers). Quantitative figures (salary, employment, growth) are
deliberately absent: they are filled only from cited sources (BLS sync, the
curated India benchmark file) and are null until then.
"""

from __future__ import annotations

# name -> (industry, regions where the firm has a well-known presence)
CO: dict[str, tuple[str, list[str]]] = {}


def _co(industry: str, regions: list[str], *names: str) -> None:
    for n in names:
        CO[n] = (industry, regions)


G = ["Global"]
_co("Investment banking", ["US", "UK", "Europe", "India", "APAC"], "Goldman Sachs", "Morgan Stanley", "JPMorgan Chase", "Citi", "Bank of America", "Deutsche Bank", "Barclays", "UBS", "Jefferies", "Nomura")
_co("Investment banking", ["India"], "Kotak Investment Banking", "ICICI Securities", "Axis Capital", "Avendus Capital", "JM Financial")
_co("Banking", ["Global", "India"], "HSBC", "Standard Chartered")
_co("Banking", ["India"], "HDFC Bank", "ICICI Bank", "State Bank of India", "Axis Bank")
_co("Asset management", ["US", "Europe", "India", "APAC"], "BlackRock", "Vanguard", "Fidelity Investments", "Franklin Templeton", "Amundi")
_co("Asset management", ["India"], "HDFC Asset Management", "SBI Funds Management", "ICICI Prudential AMC", "Nippon India AMC")
_co("Quant trading / hedge fund", ["US", "Europe", "APAC"], "Citadel", "Jane Street", "Two Sigma", "Optiver", "Jump Trading")
_co("Quant trading / hedge fund", ["US", "India"], "D. E. Shaw", "WorldQuant", "Tower Research Capital", "Graviton Research")
_co("Credit ratings & research", ["Global", "India"], "CRISIL", "S&P Global", "Moody's", "Fitch Ratings", "Morningstar", "MSCI")
_co("Credit ratings & research", ["India"], "ICRA", "CARE Ratings")
_co("Management consulting", ["Global", "India"], "McKinsey & Company", "Boston Consulting Group", "Bain & Company", "Oliver Wyman", "Kearney", "L.E.K. Consulting", "ZS Associates", "Alvarez & Marsal")
_co("Professional services", ["Global", "India"], "Deloitte", "PwC", "EY", "KPMG", "Accenture", "Genpact", "EXL")
_co("Technology", ["Global", "India"], "Google", "Microsoft", "Amazon", "Meta", "Apple", "Adobe", "Salesforce", "Oracle", "SAP", "Atlassian", "IBM", "Cisco", "Uber", "Netflix", "Intuit", "Nvidia", "Red Hat")
_co("Technology (data & AI platforms)", ["Global", "India"], "Databricks", "Snowflake", "Palantir", "OpenAI", "Anthropic", "Google DeepMind", "Hugging Face")
_co("Internet & consumer tech", ["India"], "Flipkart", "Swiggy", "Zomato", "Meesho", "CRED", "Ola", "Nykaa", "Myntra")
_co("Fintech", ["India"], "Razorpay", "Zerodha", "PhonePe", "Paytm", "Groww", "Juspay")
_co("IT services", ["Global", "India"], "Infosys", "Tata Consultancy Services", "Wipro", "HCLTech", "Tech Mahindra", "Cognizant", "Capgemini")
_co("Cybersecurity", ["Global", "India"], "CrowdStrike", "Palo Alto Networks", "Zscaler", "Mandiant (Google Cloud)", "Fortinet")
_co("Cybersecurity", ["India"], "Quick Heal", "K7 Computing")
_co("Design & product tools", ["Global", "India"], "Figma", "Canva", "Airbnb", "Spotify", "Frog Design", "IDEO")
_co("Venture capital", ["India", "US", "Global"], "Peak XV Partners", "Accel", "Lightspeed", "Elevation Capital", "Matrix Partners India", "Blume Ventures", "Sequoia Capital", "Andreessen Horowitz")
_co("Private equity", ["Global", "India"], "KKR", "Blackstone", "Carlyle", "TPG", "Bain Capital", "Warburg Pincus", "ChrysCapital", "Temasek")
_co("FMCG", ["Global", "India"], "Hindustan Unilever", "Procter & Gamble", "Nestlé", "ITC", "Tata Consumer Products", "Mondelez", "PepsiCo", "Coca-Cola")
_co("Conglomerate / manufacturing", ["India"], "Tata Group", "Reliance Industries", "Mahindra Group", "Aditya Birla Group", "Larsen & Toubro", "Maruti Suzuki")
_co("Retail & e-commerce", ["Global", "India"], "Walmart", "Target", "Reliance Retail")
_co("Logistics & supply chain", ["Global", "India"], "Maersk", "DHL", "FedEx", "Delhivery", "Blue Dart")
_co("Insurance", ["Global", "India"], "Swiss Re", "Munich Re", "Allianz", "Prudential")
_co("Insurance", ["India"], "Life Insurance Corporation of India", "HDFC Life", "ICICI Prudential Life", "Bajaj Allianz", "SBI Life")
_co("Actuarial & HR consulting", ["Global", "India"], "Milliman", "Aon", "WTW", "Mercer", "Randstad", "Korn Ferry")
_co("Law firm", ["India"], "Cyril Amarchand Mangaldas", "AZB & Partners", "Shardul Amarchand Mangaldas", "Khaitan & Co", "Trilegal", "Luthra & Luthra")
_co("Law firm", ["UK", "US", "Europe", "Global"], "Linklaters", "Clifford Chance", "A&O Shearman", "Baker McKenzie", "Skadden", "Latham & Watkins")
_co("Public policy & economics", ["India"], "Reserve Bank of India", "NITI Aayog", "NCAER", "ICRIER", "Ministry of Finance (Government of India)", "SEBI")
_co("Public policy & economics", ["Global"], "World Bank", "International Monetary Fund", "Asian Development Bank", "OECD")
_co("Research institutions", ["India"], "ISRO", "DRDO", "CSIR laboratories", "Indian Institute of Science", "Tata Institute of Fundamental Research", "IITs / IISERs")
_co("Research institutions", ["Global"], "NASA", "CERN", "Max Planck Institutes", "Microsoft Research", "Google Research", "IBM Research")
_co("Industrial technology", ["Global", "India"], "Siemens", "Bosch", "Honeywell", "GE", "Schneider Electric", "ABB")
_co("Pharma & healthcare", ["Global", "India"], "Pfizer", "Novartis", "Sun Pharma", "Dr. Reddy's", "Cipla")
_co("Startup ecosystem", ["India", "Global"], "Y Combinator", "Startup India (DPIIT)", "Antler", "T-Hub", "NASSCOM 10,000 Startups")

SOFT = {
    "Finance": ["Attention to detail", "Analytical thinking", "Written communication", "Stress management", "Integrity & discretion"],
    "Consulting": ["Structured problem solving", "Client communication", "Storytelling with data", "Teamwork under pressure", "Adaptability"],
    "Technology": ["Problem solving", "Collaboration", "Clear technical communication", "Continuous learning", "Ownership"],
    "AI & Data": ["Analytical curiosity", "Communicating insights", "Stakeholder management", "Critical thinking", "Continuous learning"],
    "Product & Design": ["Empathy for users", "Prioritisation", "Cross-functional leadership", "Communication", "Judgement with ambiguity"],
    "Business": ["Negotiation", "Leadership", "Communication", "Resilience", "Planning & organisation"],
    "Security": ["Analytical thinking", "Attention to detail", "Composure under incidents", "Ethical judgement", "Documentation"],
    "Investments & Entrepreneurship": ["Judgement under uncertainty", "Networking", "Resilience", "Persuasion", "Intellectual curiosity"],
    "Other": ["Analytical thinking", "Communication", "Attention to detail", "Time management", "Collaboration"],
}

# Editorial work-life-balance baseline per sector. Rated on a 1-5 scale where
# a higher number means a heavier load. These are qualitative editorial
# estimates (flagged as such in the UI), not survey statistics.
WLB = {
    "Finance": dict(hours="Typically 9-11 hours a day; longer around deals, results and month-end", weekend="Occasional; frequent in deal or reporting cycles", pressure=4, remote="Mostly in-office; limited hybrid", travel="Low to moderate", client="Moderate", flexibility="Low to moderate"),
    "Consulting": dict(hours="Typically 10-12 hours a day on active projects", weekend="Occasional, driven by client deadlines", pressure=4, remote="Hybrid; team days on client site", travel="Moderate to high depending on engagement", client="High", flexibility="Moderate"),
    "Technology": dict(hours="Typically 8-9 hours a day with on-call rotations in some roles", weekend="Rare, except releases or incidents", pressure=3, remote="Remote and hybrid are common", travel="Low", client="Low to moderate", flexibility="High"),
    "AI & Data": dict(hours="Typically 8-9 hours a day; deadline-driven peaks", weekend="Rare", pressure=3, remote="Remote and hybrid are common", travel="Low", client="Moderate", flexibility="High"),
    "Product & Design": dict(hours="Typically 9-10 hours a day; heavier around launches", weekend="Rare", pressure=3, remote="Hybrid is common", travel="Low", client="Moderate", flexibility="Moderate to high"),
    "Business": dict(hours="Typically 9-10 hours a day; field or target-driven peaks", weekend="Occasional", pressure=3, remote="Hybrid for many roles; field roles are on-site", travel="Moderate", client="High", flexibility="Moderate"),
    "Security": dict(hours="Typically 8-9 hours a day plus incident on-call", weekend="Occasional during incidents", pressure=4, remote="Hybrid is common", travel="Low", client="Low to moderate", flexibility="Moderate to high"),
    "Investments & Entrepreneurship": dict(hours="Often 10-12 hours a day; founder hours are open-ended", weekend="Frequent in deal or launch phases", pressure=4, remote="Varies; deal teams mostly in-office", travel="Moderate", client="Moderate to high", flexibility="Moderate"),
    "Other": dict(hours="Typically 8-9 hours a day", weekend="Rare to occasional", pressure=2, remote="Hybrid is increasingly common", travel="Low to moderate", client="Moderate", flexibility="Moderate"),
}

OUTLOOK = {
    "Finance": dict(demand="Steady demand from banks, asset managers and fintechs; hiring follows market cycles and is cyclical at the entry level.", drivers=["Growth of capital markets and wealth products", "Regulatory and risk-management requirements", "Digitisation of financial services"], emerging=["Generative AI for research and document drafting", "Automation of routine reporting", "Alternative data and machine learning in investing"], geo=["Mumbai", "Bengaluru", "Delhi NCR", "London", "New York", "Singapore"]),
    "Consulting": dict(demand="Demand tracks corporate transformation spending and is sensitive to economic cycles; AI, operations and risk work are growing practice areas.", drivers=["Digital and AI transformation programmes", "Cost and operating-model restructuring", "Regulatory change"], emerging=["Generative AI for analysis and deck drafting", "Data-driven diagnostics", "Automation of research tasks"], geo=["Mumbai", "Delhi NCR", "Bengaluru", "London", "New York", "Singapore"]),
    "Technology": dict(demand="Persistent demand for engineers, with hiring that shifts toward cloud, AI and security skills and is cyclical with funding conditions.", drivers=["Cloud migration", "AI product adoption", "Software in every industry"], emerging=["AI-assisted coding", "Platform engineering", "Edge and serverless computing"], geo=["Bengaluru", "Hyderabad", "Pune", "Chennai", "Delhi NCR", "San Francisco Bay Area", "Seattle", "London"]),
    "AI & Data": dict(demand="Strong and broadening demand as organisations operationalise analytics and AI; roles are evolving quickly.", drivers=["Enterprise AI adoption", "Growth of data volumes", "Demand for decision intelligence"], emerging=["Generative AI and LLM tooling", "MLOps and data platforms", "Automated analytics assistants"], geo=["Bengaluru", "Hyderabad", "Pune", "Gurugram", "San Francisco Bay Area", "London", "Toronto"]),
    "Product & Design": dict(demand="Steady demand in product-led companies; competitive at entry level with preference for demonstrated product thinking.", drivers=["Growth of digital products", "Focus on user experience and retention", "AI-enabled features"], emerging=["AI-assisted prototyping and research", "Design systems automation", "Product analytics tooling"], geo=["Bengaluru", "Gurugram", "Mumbai", "Hyderabad", "San Francisco Bay Area", "London"]),
    "Business": dict(demand="Broad demand across industries; growth and operations skills are valued as companies scale.", drivers=["Expansion of consumer and B2B markets", "Digital channels and marketplaces", "Supply chain modernisation"], emerging=["AI in marketing and sales workflows", "Automation of reporting", "Real-time operations analytics"], geo=["Mumbai", "Delhi NCR", "Bengaluru", "Pune", "Chennai", "Dubai", "Singapore"]),
    "Security": dict(demand="Sustained demand as threats, regulation and cloud adoption grow; qualified practitioners remain in short supply.", drivers=["Rising cyber threats", "Data-protection regulation", "Cloud and identity security"], emerging=["AI-assisted threat detection", "Zero-trust architectures", "AI-enabled attacks and defences"], geo=["Bengaluru", "Hyderabad", "Pune", "Delhi NCR", "London", "Washington DC area"]),
    "Investments & Entrepreneurship": dict(demand="Few seats and high selectivity; opportunities follow funding cycles and deal activity.", drivers=["Growth of India's startup and private-markets ecosystem", "Institutional capital in private assets"], emerging=["AI for deal sourcing and diligence", "Data-driven investing", "New fund structures"], geo=["Mumbai", "Bengaluru", "Delhi NCR", "Singapore", "London", "New York"]),
    "Other": dict(demand="Steady, specialised demand tied to the professional's sector.", drivers=["Sector growth", "Regulation and compliance", "Digitisation"], emerging=["Generative AI for drafting and research", "Automation of routine tasks", "Analytics in decision-making"], geo=["Mumbai", "Delhi NCR", "Bengaluru", "Hyderabad", "Pune", "London", "Singapore"]),
}

THEMES = {
    "Finance": "finance", "Consulting": "consulting", "Technology": "tech", "AI & Data": "data",
    "Product & Design": "product", "Business": "business", "Security": "security",
    "Investments & Entrepreneurship": "invest", "Other": "office",
}

EXIT_DEFAULT_QUAL = "Further study (MBA / specialist master's) or a relevant certification, depending on the target role"

SOURCES_COMMON = [
    ("curated", "ARJUNA AI editorial research (qualitative role description)", None, "Responsibilities, workflow, trajectory, work-life balance, exits"),
]


def career(
    title, ind, soc, onet, short, desc, resp, tech, tools, know, deg, cert, env,
    traj, cos, flow, exits, pros, cons, emerging=None, wlb=None, geo=None,
    demand=None, hq=None,
):
    """Expand a compact authored entry into the seed schema."""
    for name in cos:
        if name not in CO:
            raise KeyError(f"{title}: unknown company {name!r}")
    base_wlb = dict(WLB[ind])
    base_wlb.update(wlb or {})
    out = dict(OUTLOOK[ind])
    if emerging:
        out["emerging"] = emerging
    if demand:
        out["demand"] = demand
    if geo:
        out["geo"] = geo
    roles, inds, quals = exits
    designations = [t[0] for t in traj]
    return dict(
        title=title,
        industry=ind,
        short_description=short,
        description=desc,
        responsibilities=resp,
        industries=hq or sorted({CO[c][0] for c in cos}),
        work_environment=env,
        onet_code=onet,
        soc_code=soc,
        visual_theme=THEMES[ind],
        work_life_balance=base_wlb,
        outlook=dict(
            current_demand=out["demand"],
            growth_drivers=out["drivers"],
            emerging_technologies=out["emerging"],
            geographic_demand=out["geo"],
            employment_growth=None,
            employment_growth_note="Quantitative growth is shown only where a cited source (e.g. US BLS projections) is available.",
            basis="editorial_estimate",
        ),
        skills=dict(technical=tech, tools=tools, knowledge=know, soft=SOFT[ind]),
        qualifications=dict(degrees=deg, certifications=cert),
        trajectory=[dict(stage=i + 1, level_name=n, designation=t[0], years=[t[1], t[2]]) for i, (n, t) in enumerate(zip(["Entry", "Mid", "Senior", "Leadership"], traj))],
        companies=[dict(name=c, industry=CO[c][0], regions=CO[c][1]) for c in cos],
        exits=dict(roles=roles, industries=inds, qualifications=quals),
        advantages=[dict(aspect=a.split(":", 1)[0].strip(), note=a.split(":", 1)[1].strip()) for a in pros],
        disadvantages=[dict(aspect=a.split(":", 1)[0].strip(), note=a.split(":", 1)[1].strip()) for a in cons],
        geography=out["geo"],
        scenes_flow=[dict(heading=f[0], text=f[1], tools=f[2]) for f in flow],
        designations=designations,
    )
