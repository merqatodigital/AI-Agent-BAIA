/**
 * Concierge page presentation constants (UI-only).
 *
 * These are static, hardcoded UI suggestions for the public concierge page.
 * They are NOT derived from any backend, knowledge base, or model, and must
 * not be mistaken for live operational state. The real concierge response
 * comes from the FastAPI + CrewAI service via /api/agent.
 */

export interface SuggestedQuestion {
  id: string;
  text: string;
}

export interface PopularTopic {
  id: string;
  label: string;
}

export const SUGGESTED_QUESTIONS: SuggestedQuestion[] = [
  { id: "s1", text: "What activities are available in San Vicente?" },
  { id: "s2", text: "How do I get from the airport to the resort?" },
  { id: "s3", text: "What time is breakfast served?" },
  { id: "s4", text: "Can you recommend a local tour?" },
];

export const POPULAR_TOPICS: PopularTopic[] = [
  { id: "t1", label: "Before You Arrive" },
  { id: "t2", label: "During Your Stay" },
  { id: "t3", label: "Dining & Bars" },
  { id: "t4", label: "Tours & Nature" },
  { id: "t5", label: "Policies & FAQs" },
];
