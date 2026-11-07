/**
 * Consulting Career Story — Rohan Mehta, Consultant at Kestrel Ridge Advisory, Mumbai.
 *
 * Content is taken from the Arjuna career profile "Profile 51 / Rohan Mehta"
 * (13 sentences, 13 images). Every `source` string below is the profile sentence
 * verbatim; `paragraphs` only restate that sentence for readability and add no
 * new facts, results or projects. `method` panels explain the consulting
 * technique in general terms — they are teaching notes, not claims about this
 * engagement.
 *
 * The profile describes work spread across an engagement rather than one dated
 * day, so the story carries no clock times. `phase` carries the real sequence
 * from the profile.
 *
 * Images were extracted from the source PDF and live in
 * `public/careerverse/consulting/rohan-mehta/`.
 */

export type SceneLayout = "cinematic" | "split-left" | "split-right";

export type SceneMetric = {
  /** Short, scannable figure, e.g. "64" or "31h → 22h". */
  value: string;
  label: string;
};

export type ConsultingScene = {
  number: number;
  /** Where this sits in the real engagement sequence. */
  phase: string;
  kicker: string;
  heading: string;
  image: string;
  /** Small timeline-strip version of the same image. */
  thumb: string;
  imageAlt: string;
  /** CSS object-position, so the subject stays visible at every crop. */
  focus: string;
  layout: SceneLayout;
  /** Accent gradient stops used for the scene's ambient wash. */
  tone: [string, string];
  /** Verbatim sentence from the career profile. */
  source: string;
  paragraphs: string[];
  metrics?: SceneMetric[];
  tools?: string[];
  skills?: string[];
  /** "What is happening here?" — explains the technique, not the outcome. */
  method?: { title: string; body: string };
  takeaway?: string;
};

const DIR = "/careerverse/consulting/rohan-mehta";

/** Consulting vocabulary surfaced in the narrative, with student-facing definitions. */
export const CONSULTING_GLOSSARY: Record<string, string> = {
  MECE: "Mutually Exclusive, Collectively Exhaustive — the branches of a breakdown must not overlap, and together they must cover the whole problem.",
  "issue tree":
    "A problem broken into branches and sub-branches, so a large question becomes a set of small, testable ones.",
  "hypothesis-led diagnosis":
    "Starting with a likely answer and then testing it against evidence, instead of analysing everything and hoping a finding appears.",
  "operating margin":
    "Operating profit as a percentage of revenue — what the business keeps from each rupee of sales before interest and tax.",
  "profitability model":
    "A spreadsheet that splits revenue and cost down to a unit — here, by laboratory and by test category — to show where money is actually made or lost.",
  utilisation:
    "How much of an asset's available capacity is actually used. An expensive analyser running at 40% of capacity still costs the same to own.",
  benchmarked:
    "Compared against an outside reference point — published norms or peer performance — so a number can be judged as good or poor.",
  "price realisation":
    "The price a business actually collects after discounts and mix effects, as opposed to its list price.",
  "test mix": "The blend of cheap and expensive tests sold, which moves revenue and margin even when prices do not.",
  "send-out tests": "Tests a laboratory does not run in-house and sends to another lab, so its cost is bought rather than produced.",
  "base case": "The expected-outcome version of an estimate, against which a cautious lower version is shown as the conservative case.",
  "KPI tracker":
    "A short, fixed list of measures reviewed on a regular rhythm, so a decision keeps being checked after it is approved.",
  "weighted criteria":
    "A scoring sheet where each criterion carries an agreed weight, so options are compared on what matters rather than on impressions.",
  "integration risk": "The risk that a new system proves hard or costly to connect to the systems already running.",
  "answer-first":
    "Leading with the conclusion, then the supporting evidence — the opposite of building up to a reveal.",
  "process mapping": "Drawing a workflow step by step to see hand-offs, waiting time and where it breaks.",
  "steering update": "The regular session where the client's decision-makers review progress and unblock the work.",
  "engagement manager": "The consultant who runs the project day to day, between the analysts and the partner.",
};

export const CONSULTING_PROFILE = {
  slug: "management-consultant",
  name: "Rohan Mehta",
  role: "Consultant",
  firm: "Kestrel Ridge Advisory",
  location: "Mumbai, India",
  client: "Vaidya Diagnostics",
  title: "The Diagnosis",
  subtitle: "A consultant's engagement, from the first question to the handover note",
  summary:
    "Rohan Mehta advises mid-sized companies on operating performance and organisational change. Follow his engagement with Vaidya Diagnostics — a chain of 64 pathology laboratories losing margin — from the business question, through the issue tree and the data, to the recommendation, the rollout and the handover.",
  sourceNote:
    "Built from the Arjuna career profile “Profile 51 / Rohan Mehta” — 13 sentences and 13 original images. The scenes follow the engagement in the order the profile describes it.",
  cover: `${DIR}/scene-01.webp`,
};

export const CONSULTING_SCENES: ConsultingScene[] = [
  {
    number: 1,
    phase: "Engagement start",
    kicker: "Before anything else",
    heading: "Write down the question you were hired to answer",
    image: `${DIR}/scene-01.webp`,
    thumb: `${DIR}/thumb-01.webp`,
    imageAlt:
      "Rohan Mehta at a meeting-room table beside a window, writing the business question in a notebook.",
    focus: "50% 35%",
    layout: "cinematic",
    tone: ["#13324A", "#2F6F8F"],
    source:
      "Rohan Mehta advises mid-sized companies on operating performance and organisational change, and he begins every engagement by writing down the business question he has been hired to answer.",
    paragraphs: [
      "Rohan advises mid-sized companies on two things: how well they operate, and how they change the way they are organised.",
      "Every engagement opens the same way. Before a single analysis, he writes down the business question he has been hired to answer — in plain words, on one line.",
    ],
    skills: ["Problem definition", "Structured thinking", "Client listening"],
    method: {
      title: "Why the question comes first",
      body: "A consulting project drifts when the question is vague. Writing it down fixes the scope: every later analysis has to earn its place by moving that one question forward. If a piece of work does not answer it, it is cut.",
    },
    takeaway: "Consulting starts with framing, not with answers.",
  },
  {
    number: 2,
    phase: "The firm",
    kicker: "Kestrel Ridge Advisory",
    heading: "A team of four to six, a manager and a partner",
    image: `${DIR}/scene-02.webp`,
    thumb: `${DIR}/thumb-02.webp`,
    imageAlt: "Rohan and colleagues working together in the Kestrel Ridge Advisory office in Mumbai.",
    focus: "50% 40%",
    layout: "split-right",
    tone: ["#163A52", "#3A7FA0"],
    source:
      "At Kestrel Ridge Advisory, his employer, a Mumbai consultancy of about 180 people that blends strategy, operations and technology work, he works in teams of four to six led by an engagement manager and a partner.",
    paragraphs: [
      "His employer, Kestrel Ridge Advisory, is a Mumbai consultancy of about 180 people. Its work blends strategy, operations and technology rather than sitting in one of them.",
      "Work happens in small teams of four to six people, led by an engagement manager and a partner.",
    ],
    metrics: [
      { value: "~180", label: "People in the firm" },
      { value: "4–6", label: "Consultants per team" },
      { value: "3", label: "Practice areas blended" },
    ],
    skills: ["Teamwork", "Working to a manager", "Partner communication"],
    method: {
      title: "Who sits where",
      body: "A typical structure: analysts and consultants do the analysis, the engagement manager runs the project day to day, and the partner owns the client relationship and the final recommendation. Feedback flows down that line quickly.",
    },
  },
  {
    number: 3,
    phase: "The brief",
    kicker: "Client: Vaidya Diagnostics",
    heading: "64 laboratories, four points of margin gone",
    image: `${DIR}/scene-03.webp`,
    thumb: `${DIR}/thumb-03.webp`,
    imageAlt: "A pathology laboratory of the Vaidya Diagnostics chain during working hours.",
    focus: "50% 45%",
    layout: "cinematic",
    tone: ["#10303F", "#2E7F86"],
    source:
      "His main engagement was for Vaidya Diagnostics, a chain of 64 pathology laboratories whose operating margin had slipped by four points in two years while complaints about late reports kept rising.",
    paragraphs: [
      "His main engagement was for Vaidya Diagnostics, a chain of 64 pathology laboratories.",
      "Two symptoms sat on the table. The operating margin had slipped by four points over two years. At the same time, complaints about late reports kept rising.",
      "Two problems, one business — and no agreement yet on whether they share a cause.",
    ],
    metrics: [
      { value: "64", label: "Pathology laboratories" },
      { value: "−4 pts", label: "Operating margin, over two years" },
      { value: "Rising", label: "Complaints about late reports" },
    ],
    skills: ["Reading a client situation", "Separating symptom from cause"],
    takeaway: "Clients arrive with symptoms. The cause is the consultant's job to find.",
  },
  {
    number: 4,
    phase: "Week 1–2 · Diagnosis",
    kicker: "Hypothesis-led diagnosis",
    heading: "A MECE issue tree, fourteen interviews, two courier routes",
    image: `${DIR}/scene-04.webp`,
    thumb: `${DIR}/thumb-04.webp`,
    imageAlt: "Rohan drawing a MECE issue tree on a whiteboard while structuring the problem.",
    focus: "50% 38%",
    layout: "split-left",
    tone: ["#1A3357", "#4169A8"],
    source:
      "He spent the first fortnight on a hypothesis-led diagnosis, drawing a MECE issue tree across volume, price, test mix and cost, interviewing fourteen laboratory managers and riding along on two courier routes.",
    paragraphs: [
      "The first fortnight went to a hypothesis-led diagnosis. He drew a MECE issue tree with four branches: volume, price, test mix and cost.",
      "Then he went to the people and the place. Fourteen laboratory managers were interviewed, and he rode along on two courier routes to see the operation move.",
    ],
    metrics: [
      { value: "2 weeks", label: "Spent on diagnosis" },
      { value: "4", label: "Issue-tree branches" },
      { value: "14", label: "Laboratory managers interviewed" },
      { value: "2", label: "Courier routes ridden" },
    ],
    tools: ["Whiteboard", "Issue tree", "Structured interviews", "Site visits"],
    skills: ["MECE structuring", "Hypothesis testing", "Field observation", "Interviewing"],
    method: {
      title: "What MECE means in practice",
      body: "The four branches — volume, price, test mix and cost — do not overlap, and between them they cover every way margin can move. That is what MECE buys you: no double counting, and nothing quietly left out. Each branch then becomes a question you can test with data or with an interview.",
    },
    takeaway: "Structure on the whiteboard, evidence from the floor. A consultant needs both.",
  },
  {
    number: 5,
    phase: "Analysis",
    kicker: "SQL, Excel, benchmarks",
    heading: "Fourteen months of records, laboratory by laboratory",
    image: `${DIR}/scene-05.webp`,
    thumb: `${DIR}/thumb-05.webp`,
    imageAlt: "Rohan at a two-monitor desk with the Vaidya profitability model in Excel and a SQL query open.",
    focus: "50% 45%",
    layout: "split-right",
    tone: ["#2A2150", "#5E4CA0"],
    source:
      "He pulled fourteen months of test-level records with SQL, built a profitability model in Excel by laboratory and test category, and benchmarked analyser utilisation against published norms.",
    paragraphs: [
      "He pulled fourteen months of test-level records with SQL — the transaction grain, not a summary.",
      "In Excel he built a profitability model that cut the business two ways: by laboratory, and by test category.",
      "Then he benchmarked analyser utilisation against published norms, so the numbers could be judged against something outside the client.",
    ],
    metrics: [
      { value: "14 months", label: "Of test-level records" },
      { value: "2 cuts", label: "By laboratory and by test category" },
    ],
    tools: ["SQL", "Excel", "Published industry norms"],
    skills: ["Data extraction", "Profitability analysis", "Benchmarking"],
    method: {
      title: "Why go down to test level",
      body: "Averages hide the problem. A chain can look healthy overall while a handful of sites lose money on a handful of test categories. Pulling the lowest grain of data and then cutting it by site and by category is what makes the loss-making pockets visible.",
    },
  },
  {
    number: 6,
    phase: "Working session",
    kicker: "Testing the client's own theory",
    heading: "It was not the price. It was the idle capacity",
    image: `${DIR}/scene-06.webp`,
    thumb: `${DIR}/thumb-06.webp`,
    imageAlt: "Rohan presenting analysis in a working session with the client's finance head and team.",
    focus: "50% 40%",
    layout: "cinematic",
    tone: ["#163A52", "#36718F"],
    source:
      "When the finance head blamed competitor price cuts, he showed in a working session that price realisation had barely changed, while nine small laboratories ran their analysers at under forty percent of capacity.",
    paragraphs: [
      "The finance head had an explanation ready: competitors had cut prices.",
      "In a working session, Rohan showed the data instead. Price realisation had barely changed.",
      "What had changed sat elsewhere — nine small laboratories were running their analysers at under forty percent of capacity.",
    ],
    metrics: [
      { value: "9", label: "Small laboratories flagged" },
      { value: "<40%", label: "Analyser capacity in use" },
      { value: "~Flat", label: "Price realisation" },
    ],
    tools: ["Excel model", "Working session"],
    skills: ["Disconfirming a hypothesis", "Evidence-based challenge", "Stakeholder handling"],
    method: {
      title: "Disagreeing with the client, usefully",
      body: "The finance head's theory was reasonable — it just did not survive the data. A working session is the format for that: the analysis is walked through together rather than delivered as a verdict, so the client arrives at the conclusion with you instead of defending against it.",
    },
    takeaway: "The most valuable finding is often the one that rules out the obvious explanation.",
  },
  {
    number: 7,
    phase: "Recommendation",
    kicker: "Three moves, costed conservatively",
    heading: "Nine laboratories into three regional hubs",
    image: `${DIR}/scene-07.webp`,
    thumb: `${DIR}/thumb-07.webp`,
    imageAlt: "Rohan presenting the recommendation to senior stakeholders in the client's boardroom.",
    focus: "50% 38%",
    layout: "split-left",
    tone: ["#12324A", "#2F6F8F"],
    source:
      "He recommended consolidating those nine laboratories into three regional hubs, fixing courier pickup windows and repricing a few send-out tests, with a conservative savings case at about sixty percent of the base case.",
    paragraphs: [
      "The recommendation had three moves: consolidate the nine laboratories into three regional hubs, fix courier pickup windows, and reprice a few send-out tests.",
      "He did not present the optimistic number alone. Alongside the base case he put a conservative savings case at about sixty percent of it.",
    ],
    metrics: [
      { value: "9 → 3", label: "Laboratories into regional hubs" },
      { value: "Fixed", label: "Courier pickup windows" },
      { value: "~60%", label: "Conservative case vs base case" },
    ],
    tools: ["PowerPoint", "Excel savings case"],
    skills: ["Recommendation design", "Sizing the prize", "Executive presentation"],
    method: {
      title: "Why show the cautious number",
      body: "A recommendation that only shows its best case invites the client to discount all of it. Presenting a conservative case next to the base case tells the board what the decision is still worth if things go less well than hoped — which is the number they will actually commit against.",
    },
    takeaway: "Credibility comes from the downside case, not the upside one.",
  },
  {
    number: 8,
    phase: "Implementation",
    kicker: "Phased rollout, tracked weekly",
    heading: "31 hours to 22, and 2.6 points of margin back",
    image: `${DIR}/scene-08.webp`,
    thumb: `${DIR}/thumb-08.webp`,
    imageAlt: "A weekly KPI tracker dashboard showing turnaround time and margin recovery during the rollout.",
    focus: "50% 42%",
    layout: "cinematic",
    tone: ["#0C3326", "#2B6B4E"],
    source:
      "After the board approved a phased rollout, he set up a weekly KPI tracker, and within two quarters report turnaround fell from 31 hours to 22 and operating margin recovered by 2.6 points.",
    paragraphs: [
      "The board approved a phased rollout, and the work did not end at approval.",
      "Rohan set up a weekly KPI tracker so the change kept being measured while it happened.",
      "Within two quarters, report turnaround fell from 31 hours to 22, and operating margin recovered by 2.6 points.",
    ],
    metrics: [
      { value: "31h → 22h", label: "Report turnaround" },
      { value: "+2.6 pts", label: "Operating margin recovered" },
      { value: "2 quarters", label: "Time to that result" },
      { value: "Weekly", label: "KPI review rhythm" },
    ],
    tools: ["KPI tracker", "Power BI", "Excel"],
    skills: ["Implementation support", "KPI design", "Change tracking"],
    method: {
      title: "Why the tracker matters",
      body: "A phased rollout can drift quietly. A short weekly measure — turnaround time, margin, volumes — turns drift into something visible in days rather than quarters, and gives the client a reason to keep going when the first weeks look flat.",
    },
    takeaway: "A recommendation is a hypothesis until the KPIs move.",
  },
  {
    number: 9,
    phase: "Second engagement",
    kicker: "Regional insurer · claims platform",
    heading: "Four vendors, scored on what actually matters",
    image: `${DIR}/scene-09.webp`,
    thumb: `${DIR}/thumb-09.webp`,
    imageAlt: "Rohan running a vendor evaluation session, comparing claims platform options on a scoring matrix.",
    focus: "50% 40%",
    layout: "split-right",
    tone: ["#2A2150", "#55479B"],
    source:
      "In a shorter assignment for a regional insurer, he ran the vendor selection for a claims platform, scoring four vendors on weighted criteria and recommending the second-ranked product because its integration risk and five-year cost were lower.",
    paragraphs: [
      "A shorter assignment, for a regional insurer: run the vendor selection for a claims platform.",
      "He scored four vendors on weighted criteria — and then recommended the second-ranked product, not the first.",
      "The reason was in two columns of the scoresheet: its integration risk and its five-year cost were lower.",
    ],
    metrics: [
      { value: "4", label: "Vendors scored" },
      { value: "#2", label: "Rank of the recommended product" },
      { value: "5 years", label: "Cost horizon compared" },
    ],
    tools: ["Weighted scoring matrix", "Excel", "Vendor demos"],
    skills: ["Vendor evaluation", "Total cost of ownership", "Risk assessment"],
    method: {
      title: "When the top-ranked option is not the answer",
      body: "A weighted scoresheet ranks features, but the decision is a business one. Integration risk and the cost over a realistic ownership horizon can outweigh a feature lead — and saying so plainly is part of the recommendation.",
    },
    takeaway: "Pick the option the client can actually run, not the one that demos best.",
  },
  {
    number: 10,
    phase: "The weekly rhythm",
    kicker: "How the week is shaped",
    heading: "Check-in, client work, steering update, slides",
    image: `${DIR}/scene-10.webp`,
    thumb: `${DIR}/thumb-10.webp`,
    imageAlt: "The consulting team in a Monday check-in meeting at the start of the working week.",
    focus: "50% 38%",
    layout: "cinematic",
    tone: ["#163A52", "#3A7FA0"],
    source:
      "A typical week opens with a Monday team check-in, fills the middle days with client interviews and data work, and ends with a Friday steering update, with evenings spent rewriting slides until each title states its conclusion.",
    paragraphs: [
      "A typical week opens with a Monday team check-in.",
      "The middle days go to client interviews and data work — the two halves of the evidence.",
      "Friday closes with a steering update. Evenings go to rewriting slides, until every title states its conclusion rather than its topic.",
    ],
    metrics: [
      { value: "Monday", label: "Team check-in" },
      { value: "Tue–Thu", label: "Interviews and data work" },
      { value: "Friday", label: "Steering update" },
    ],
    tools: ["PowerPoint", "Interview guides", "Excel"],
    skills: ["Time management", "Slide writing", "Client cadence"],
    method: {
      title: "“Each title states its conclusion”",
      body: "On a consulting slide the headline is the finding — “Nine labs run under 40% utilisation” — not the subject — “Utilisation analysis”. Read the titles alone, top to bottom, and the argument should hold together without the charts.",
    },
    takeaway: "The deck is not a record of the work. It is the argument.",
  },
  {
    number: 11,
    phase: "Feedback culture",
    kicker: "Direct, and fast",
    heading: "Partners mark up the slides within hours",
    image: `${DIR}/scene-11.webp`,
    thumb: `${DIR}/thumb-11.webp`,
    imageAlt: "A partner reviewing and marking up Rohan's slides during a feedback session.",
    focus: "50% 40%",
    layout: "split-left",
    tone: ["#12324A", "#2F6F8F"],
    source:
      "Feedback in the firm is frequent and direct, so partners mark up his slides within hours, and he presents to senior executives answer-first, with the evidence ready for the questions he expects.",
    paragraphs: [
      "Feedback inside the firm is frequent and direct. Partners mark up his slides within hours, not at the end of a phase.",
      "In front of senior executives he presents answer-first: the conclusion opens, the evidence follows.",
      "The supporting material is prepared for the questions he expects, not for every question that could be asked.",
    ],
    tools: ["PowerPoint", "Partner review", "Backup appendix"],
    skills: ["Receiving feedback", "Answer-first communication", "Anticipating objections"],
    method: {
      title: "Answer-first, in one line",
      body: "Executives give you the first minute, not the last. Leading with the conclusion lets them spend the remaining time testing it — which is where the real value of the session is.",
    },
    takeaway: "Fast, direct feedback is the training. Take the mark-up, not the offence.",
  },
  {
    number: 12,
    phase: "Skills and background",
    kicker: "What he works with, and how he got here",
    heading: "Excel, PowerPoint, SQL, Power BI, process mapping",
    image: `${DIR}/scene-12.webp`,
    thumb: `${DIR}/thumb-12.webp`,
    imageAlt: "Rohan's working setup showing the consulting toolkit he uses day to day.",
    focus: "50% 42%",
    layout: "split-right",
    tone: ["#1A3357", "#4169A8"],
    source:
      "His toolkit includes Excel, PowerPoint, SQL, Power BI and process mapping, and he holds a mechanical engineering degree from Veermata Jijabai Technological Institute and an MBA from the Indian School of Business.",
    paragraphs: [
      "The toolkit is short and used hard: Excel, PowerPoint, SQL, Power BI and process mapping.",
      "His background is a mechanical engineering degree from Veermata Jijabai Technological Institute, followed by an MBA from the Indian School of Business.",
    ],
    tools: ["Excel", "PowerPoint", "SQL", "Power BI", "Process mapping"],
    skills: ["Quantitative analysis", "Data querying", "Dashboarding", "Operations modelling"],
    method: {
      title: "An engineering-to-MBA route",
      body: "Engineering first, MBA second is a common path into consulting in India: the degree supplies the quantitative and process instinct, the MBA supplies the business framing and the recruiting route.",
    },
  },
  {
    number: 13,
    phase: "Handover",
    kicker: "The last document",
    heading: "What the client should keep measuring",
    image: `${DIR}/scene-13.webp`,
    thumb: `${DIR}/thumb-13.webp`,
    imageAlt: "Rohan handing over the closing note to the client team at the end of the engagement.",
    focus: "50% 38%",
    layout: "cinematic",
    tone: ["#0C3326", "#2E8C86"],
    source:
      "He ends every engagement with a handover note listing what the client should keep measuring, because a recommendation only counts once the client can run it without the consultants.",
    paragraphs: [
      "Every engagement ends with a handover note, and the note is a list: what the client should keep measuring.",
      "The reasoning behind it is the whole job in one sentence — a recommendation only counts once the client can run it without the consultants.",
    ],
    tools: ["Handover note", "KPI tracker"],
    skills: ["Knowledge transfer", "Client self-sufficiency", "Documentation"],
    method: {
      title: "Designing yourself out",
      body: "The measure of a good engagement is what survives after the team leaves. A handover note names the owners, the metrics and the review rhythm, so the change keeps being managed by people who are still there.",
    },
    takeaway: "The consultant leaves. The measurement has to stay.",
  },
];

export const CONSULTING_SCENE_COUNT = CONSULTING_SCENES.length;
