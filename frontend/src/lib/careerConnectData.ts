export type CareerDomain = "Investment Banking" | "Data Science" | "Machine Learning" | "Software Engineering" | "Product Management" | "Cybersecurity" | "Consulting" | "Marketing";

export type OpportunitySource = { name: string; url: string; kind: "individual listing" | "job search" };
export type Opportunity = {
  id: string;
  domain: CareerDomain;
  title: string;
  company: string;
  location: string;
  employmentType: "Internship" | "Full-time";
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
export const COMPANIES = ["Morgan Stanley", "JPMorgan", "Goldman Sachs", "Barclays", "Citi", "Indeed", "LinkedIn", "Wellfound", "IDFC FIRST Bank", "Other"];

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

