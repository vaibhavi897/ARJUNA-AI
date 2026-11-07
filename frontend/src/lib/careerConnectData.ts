export type CareerDomain = "Investment Banking" | "Data Science" | "Machine Learning" | "Software Engineering" | "Product Management" | "Cybersecurity" | "Consulting" | "Marketing";

export type OpportunityType = "Internship" | "Full-time" | "Hackathon" | "Case competition" | "Certification";
export const OPPORTUNITY_TYPES: { value: OpportunityType; label: string }[] = [
  { value: "Internship", label: "Internships" },
  { value: "Full-time", label: "Full-time jobs" },
  { value: "Hackathon", label: "Hackathons" },
  { value: "Case competition", label: "Case competitions" },
  { value: "Certification", label: "Certifications" },
];

export type OpportunitySource = { name: string; url: string; kind: "individual listing" | "job search" };
export type Opportunity = {
  id: string;
  domain: CareerDomain | "All domains";
  title: string;
  company: string;
  location: string;
  employmentType: OpportunityType;
  sources: OpportunitySource[];
};
export type Professional = {
  id: string;
  domain: CareerDomain;
  name: string;
  designation: string;
  company: string;
  location?: string;
  url: string;
};

export const DOMAINS: CareerDomain[] = [
  "Investment Banking",
  "Data Science",
  "Machine Learning",
  "Software Engineering",
  "Product Management",
  "Cybersecurity",
  "Consulting",
  "Marketing",
];
export const COMPANIES = ["Morgan Stanley", "JPMorgan", "Goldman Sachs", "Barclays", "Citi", "Indeed", "LinkedIn", "Wellfound", "IDFC FIRST Bank", "Internshala", "Unstop", "Devpost", "HackerEarth", "Kaggle", "Coursera", "Google", "AWS", "Microsoft", "CompTIA", "ISC2", "CFA Institute", "Other"];

export const OPPORTUNITIES: Opportunity[] = [
  { id: "ib-ms-analyst-mumbai", domain: "Investment Banking", title: "Investment Banking Division Analyst", company: "Morgan Stanley", location: "Mumbai, India", employmentType: "Full-time", sources: [{ name: "LinkedIn · Individual listing", url: "https://in.linkedin.com/jobs/view/investment-banking-division-analyst-investment-banking-mumbai-at-morgan-stanley-4477983732", kind: "individual listing" }] },
  { id: "ib-analyst-mumbai", domain: "Investment Banking", title: "Investment Banking Analyst · Mumbai search", company: "Indeed", location: "Mumbai, India", employmentType: "Full-time", sources: [{ name: "Indeed · Job search", url: "https://in.indeed.com/jobs?l=Mumbai%2C+Maharashtra&q=Investment+Banking+Analyst", kind: "job search" }] },
  { id: "ib-analyst-india", domain: "Investment Banking", title: "Investment Banking Analyst · India search", company: "Indeed", location: "India", employmentType: "Full-time", sources: [{ name: "Indeed · Job search", url: "https://in.indeed.com/Investment-Banking-Analyst-jobs-in-India", kind: "job search" }] },
  { id: "ib-linkedin-analyst", domain: "Investment Banking", title: "Investment Banking Analyst jobs", company: "LinkedIn", location: "India", employmentType: "Full-time", sources: [{ name: "LinkedIn · Job search", url: "https://in.linkedin.com/jobs/investment-banking-analyst-jobs", kind: "job search" }] },
  { id: "ib-jpmorgan", domain: "Investment Banking", title: "JPMorgan Investment Banking jobs", company: "JPMorgan", location: "India", employmentType: "Full-time", sources: [{ name: "LinkedIn · Job search", url: "https://in.linkedin.com/jobs/jpmorgan-chase-investment-banking-jobs", kind: "job search" }] },
  { id: "ds-linkedin", domain: "Data Science", title: "Data Science jobs", company: "LinkedIn", location: "India", employmentType: "Full-time", sources: [{ name: "LinkedIn · Job search", url: "https://in.linkedin.com/jobs/data-science-jobs", kind: "job search" }] },
  { id: "ds-indeed-mumbai", domain: "Data Science", title: "Data Scientist · Mumbai search", company: "Indeed", location: "Mumbai, India", employmentType: "Full-time", sources: [{ name: "Indeed · Job search", url: "https://in.indeed.com/jobs?q=Data+Scientist&l=Mumbai", kind: "job search" }] },
  { id: "ds-wellfound-science", domain: "Data Science", title: "Data Science jobs · India", company: "Wellfound", location: "India", employmentType: "Full-time", sources: [{ name: "Wellfound · Job search", url: "https://wellfound.com/role/l/data-science/india", kind: "job search" }] },
  { id: "ds-wellfound-scientist", domain: "Data Science", title: "Data Scientist jobs · India", company: "Wellfound", location: "India", employmentType: "Full-time", sources: [{ name: "Wellfound · Job search", url: "https://wellfound.com/role/l/data-scientist/india", kind: "job search" }] },
  { id: "ds-linkedin-scientist", domain: "Data Science", title: "Data Scientist jobs", company: "LinkedIn", location: "India", employmentType: "Full-time", sources: [{ name: "LinkedIn · Job search", url: "https://in.linkedin.com/jobs/data-scientist-jobs", kind: "job search" }] },
];

export const PROFESSIONALS: Professional[] = [
  { id: "p-krutarth-doshi", domain: "Investment Banking", name: "Krutarth Doshi", designation: "Investment Banking Analyst", company: "Morgan Stanley", url: "https://in.linkedin.com/in/krutarth-doshi-288b86255" },
  { id: "p-pari-gupta", domain: "Investment Banking", name: "Pari Gupta", designation: "Investment Banking Analyst", company: "Morgan Stanley", url: "https://in.linkedin.com/in/pari-gupta-0a7001194" },
  { id: "p-bharati-kamat", domain: "Investment Banking", name: "Bharati Kamat", designation: "Corporate Investment Banking", company: "Morgan Stanley", url: "https://in.linkedin.com/in/bharati-kamat" },
  { id: "p-aditya-aware", domain: "Data Science", name: "Aditya Aware", designation: "Data Scientist", company: "Morgan Stanley", url: "https://in.linkedin.com/in/adityaaware" },
  { id: "p-aditya-rai", domain: "Data Science", name: "Aditya Rai", designation: "Data Scientist", company: "Not specified", location: "Mumbai", url: "https://in.linkedin.com/in/aditya-rai-datascientist" },
  { id: "p-ishita-pawaskar", domain: "Data Science", name: "Ishita Pawaskar", designation: "Data Scientist / Business Analyst", company: "IDFC FIRST Bank", url: "https://in.linkedin.com/in/ishita-pawaskar-243b38188" },
  { id: "p-tejas-gawali", domain: "Data Science", name: "Tejas Gawali", designation: "Data Scientist", company: "Not specified", url: "https://in.linkedin.com/in/tejas-gawali-087b7b2a7" },
];

// ---- Internships, hackathons, case competitions and certifications.
// These are SEARCH and LISTING pages on the real platforms, not individual postings: dates and eligibility change,
// so each card opens the live listing page rather than showing details that could go stale.
const q = encodeURIComponent;
const src = (name: string, url: string): OpportunitySource => ({ name: `${name} · Search`, url, kind: "job search" });

const INTERN_KEYWORDS: Record<CareerDomain, string> = {
  "Investment Banking": "investment banking", "Data Science": "data science", "Machine Learning": "machine learning",
  "Software Engineering": "software engineering", "Product Management": "product management", Cybersecurity: "cyber security",
  Consulting: "consulting", Marketing: "marketing",
};
const slug = (t: string) => t.toLowerCase().replace(/\s+/g, "-");

export const EXTRA_OPPORTUNITIES: Opportunity[] = [
  ...DOMAINS.map((d): Opportunity => ({
    id: `intern-${slug(d)}`, domain: d, title: `${d} internships`, company: "Internshala", location: "India · Remote and on-site", employmentType: "Internship",
    sources: [
      src("Internshala", `https://internshala.com/internships/keywords-${slug(INTERN_KEYWORDS[d])}`),
      src("LinkedIn", `https://www.linkedin.com/jobs/search/?keywords=${q(INTERN_KEYWORDS[d] + " intern")}&location=India`),
    ],
  })),
  { id: "hack-devpost", domain: "All domains", title: "Online hackathons", company: "Devpost", location: "Online", employmentType: "Hackathon", sources: [src("Devpost", "https://devpost.com/hackathons")] },
  { id: "hack-unstop", domain: "All domains", title: "Hackathons in India", company: "Unstop", location: "India · Online and on-site", employmentType: "Hackathon", sources: [src("Unstop", "https://unstop.com/hackathons")] },
  { id: "hack-hackerearth", domain: "Software Engineering", title: "Coding hackathons and challenges", company: "HackerEarth", location: "Online", employmentType: "Hackathon", sources: [src("HackerEarth", "https://www.hackerearth.com/challenges/hackathon/")] },
  { id: "hack-kaggle", domain: "Data Science", title: "Data science competitions", company: "Kaggle", location: "Online", employmentType: "Hackathon", sources: [src("Kaggle", "https://www.kaggle.com/competitions")] },
  { id: "hack-kaggle-ml", domain: "Machine Learning", title: "Machine learning competitions", company: "Kaggle", location: "Online", employmentType: "Hackathon", sources: [src("Kaggle", "https://www.kaggle.com/competitions")] },
  { id: "case-unstop", domain: "All domains", title: "Case competitions", company: "Unstop", location: "India · Online and on-site", employmentType: "Case competition", sources: [src("Unstop", "https://unstop.com/competitions")] },
  { id: "case-consulting", domain: "Consulting", title: "Consulting case competitions", company: "Unstop", location: "India", employmentType: "Case competition", sources: [src("Unstop", `https://unstop.com/competitions?searchTerm=${q("consulting case")}`)] },
  { id: "case-ib", domain: "Investment Banking", title: "Finance and valuation case competitions", company: "Unstop", location: "India", employmentType: "Case competition", sources: [src("Unstop", `https://unstop.com/competitions?searchTerm=${q("finance case")}`)] },
  { id: "case-product", domain: "Product Management", title: "Product case competitions", company: "Unstop", location: "India", employmentType: "Case competition", sources: [src("Unstop", `https://unstop.com/competitions?searchTerm=${q("product case")}`)] },
  { id: "case-marketing", domain: "Marketing", title: "Marketing case competitions", company: "Unstop", location: "India", employmentType: "Case competition", sources: [src("Unstop", `https://unstop.com/competitions?searchTerm=${q("marketing case")}`)] },
  { id: "cert-google", domain: "All domains", title: "Google Career Certificates", company: "Google", location: "Online", employmentType: "Certification", sources: [src("Google", "https://grow.google/certificates/")] },
  { id: "cert-coursera-ds", domain: "Data Science", title: "Data science certificates", company: "Coursera", location: "Online", employmentType: "Certification", sources: [src("Coursera", `https://www.coursera.org/search?query=${q("data science professional certificate")}`)] },
  { id: "cert-coursera-ml", domain: "Machine Learning", title: "Machine learning certificates", company: "Coursera", location: "Online", employmentType: "Certification", sources: [src("Coursera", `https://www.coursera.org/search?query=${q("machine learning specialization")}`)] },
  { id: "cert-aws", domain: "Software Engineering", title: "Cloud certifications", company: "AWS", location: "Online exam", employmentType: "Certification", sources: [src("AWS", "https://aws.amazon.com/certification/")] },
  { id: "cert-microsoft", domain: "Software Engineering", title: "Microsoft role-based certifications", company: "Microsoft", location: "Online exam", employmentType: "Certification", sources: [src("Microsoft Learn", "https://learn.microsoft.com/en-us/credentials/browse/")] },
  { id: "cert-comptia", domain: "Cybersecurity", title: "Security certifications", company: "CompTIA", location: "Online exam", employmentType: "Certification", sources: [src("CompTIA", "https://www.comptia.org/certifications")] },
  { id: "cert-isc2", domain: "Cybersecurity", title: "CISSP and entry-level security certs", company: "ISC2", location: "Online exam", employmentType: "Certification", sources: [src("ISC2", "https://www.isc2.org/certifications")] },
  { id: "cert-cfa", domain: "Investment Banking", title: "CFA Program", company: "CFA Institute", location: "Online exam", employmentType: "Certification", sources: [src("CFA Institute", "https://www.cfainstitute.org/programs/cfa-program")] },
  { id: "cert-coursera-pm", domain: "Product Management", title: "Product management certificates", company: "Coursera", location: "Online", employmentType: "Certification", sources: [src("Coursera", `https://www.coursera.org/search?query=${q("product management certificate")}`)] },
  { id: "cert-coursera-mkt", domain: "Marketing", title: "Digital marketing certificates", company: "Coursera", location: "Online", employmentType: "Certification", sources: [src("Coursera", `https://www.coursera.org/search?query=${q("digital marketing certificate")}`)] },
  { id: "cert-coursera-cons", domain: "Consulting", title: "Strategy and business analysis certificates", company: "Coursera", location: "Online", employmentType: "Certification", sources: [src("Coursera", `https://www.coursera.org/search?query=${q("business strategy specialization")}`)] },
];
OPPORTUNITIES.push(...EXTRA_OPPORTUNITIES);
