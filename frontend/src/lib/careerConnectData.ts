export type Opportunity = { id: string; name: string; description: string; domains: string[]; audience: string; scope: string; category: string; url: string };
export type Competition = { id: string; name: string; organiser: string; domain: string; category: "Hackathon" | "Case competition"; eligibility: string; team_requirements: string; mode: string; prizes: string; registration: string; requirements: string; url: string; verified: string };
export type CareerDirectory = { jobs: Opportunity[]; internships: Opportunity[]; competitions: Competition[]; counts: { jobs: number; internships: number; competitions: number } };
export type OpportunityType = "Jobs" | "Internships" | "Hackathons" | "Case Competitions" | "Certifications";
export const OPPORTUNITY_TYPES: OpportunityType[] = ["Jobs", "Internships", "Hackathons", "Case Competitions", "Certifications"];
export type Professional = { id: string; domain: string; name: string; designation: string; company: string; location?: string; url: string };
export const DOMAINS = ["Software Engineering", "Data Science", "Machine Learning", "Product Management", "Cybersecurity", "Investment Banking", "Consulting", "Marketing", "Core Engineering", "Government", "All domains"];
export const PROFESSIONALS: Professional[] = [
  { id: "p-krutarth-doshi", domain: "Investment Banking", name: "Krutarth Doshi", designation: "Investment Banking Analyst", company: "Morgan Stanley", url: "https://in.linkedin.com/in/krutarth-doshi-288b86255" },
  { id: "p-pari-gupta", domain: "Investment Banking", name: "Pari Gupta", designation: "Investment Banking Analyst", company: "Morgan Stanley", url: "https://in.linkedin.com/in/pari-gupta-0a7001194" },
  { id: "p-bharati-kamat", domain: "Investment Banking", name: "Bharati Kamat", designation: "Corporate Investment Banking", company: "Morgan Stanley", url: "https://in.linkedin.com/in/bharati-kamat" },
  { id: "p-aditya-aware", domain: "Data Science", name: "Aditya Aware", designation: "Data Scientist", company: "Morgan Stanley", url: "https://in.linkedin.com/in/adityaaware" },
  { id: "p-aditya-rai", domain: "Data Science", name: "Aditya Rai", designation: "Data Scientist", company: "Not specified", location: "Mumbai", url: "https://in.linkedin.com/in/aditya-rai-datascientist" },
  { id: "p-ishita-pawaskar", domain: "Data Science", name: "Ishita Pawaskar", designation: "Data Scientist / Business Analyst", company: "IDFC FIRST Bank", url: "https://in.linkedin.com/in/ishita-pawaskar-243b38188" },
  { id: "p-tejas-gawali", domain: "Data Science", name: "Tejas Gawali", designation: "Data Scientist", company: "Not specified", url: "https://in.linkedin.com/in/tejas-gawali-087b7b2a7" },
];
