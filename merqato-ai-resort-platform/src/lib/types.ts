// Domain model for the MerQato AI Resort Website platform.
// All business data is editable and stored per-resort — nothing is hardcoded
// in the UI. These types are the single source of truth shared by the data
// layer, agents, and UI.

export type ID = string;

export interface Faq {
  id: ID;
  question: string;
  answer: string;
}

export interface Room {
  id: ID;
  name: string;
  description: string;
  pricePerNight: number;
  capacity: number;
  imageUrl: string;
}

export interface Tour {
  id: ID;
  name: string;
  description: string;
  duration: string;
  price: number;
}

export interface Restaurant {
  id: ID;
  name: string;
  cuisine: string;
  hours: string;
}

export interface TransportInfo {
  airport: string;
  airportDistanceKm: number;
  notes: string;
}

export interface EmergencyContact {
  id: ID;
  label: string;
  phone: string;
}

export interface ResortProfile {
  id: ID;
  name: string;
  tagline: string;
  description: string;
  location: string;
  heroImageUrl: string;
  contactEmail: string;
  contactPhone: string;
  amenities: string[];
  policies: string;
  faqs: Faq[];
  rooms: Room[];
  tours: Tour[];
  restaurants: Restaurant[];
  transport: TransportInfo;
  emergencyContacts: EmergencyContact[];
}

export type InquiryStatus = "new" | "contacted" | "booked" | "lost";

export interface Inquiry {
  id: ID;
  name: string;
  email: string;
  message: string;
  checkIn?: string;
  checkOut?: string;
  guests?: number;
  status: InquiryStatus;
  createdAt: string;
}

export type BookingStatus = "pending" | "confirmed" | "cancelled" | "completed";

export interface Booking {
  id: ID;
  guestName: string;
  roomId: string;
  checkIn: string;
  checkOut: string;
  guests: number;
  status: BookingStatus;
  createdAt: string;
}

export type TaskType = "housekeeping" | "maintenance";
export type TaskStatus = "todo" | "in_progress" | "done";

export interface Task {
  id: ID;
  type: TaskType;
  title: string;
  description?: string;
  status: TaskStatus;
  assignee?: string;
  due?: string;
  createdAt: string;
}

export type ApprovalStatus = "pending" | "approved" | "rejected";

export interface Approval {
  id: ID;
  action: string;
  description: string;
  requestedBy: string;
  status: ApprovalStatus;
  createdAt: string;
}

export interface AIChat {
  id: ID;
  guestName: string;
  message: string;
  response: string;
  escalated: boolean;
  createdAt: string;
}

export interface BlogPost {
  id: ID;
  title: string;
  slug: string;
  excerpt: string;
  body: string;
  published: boolean;
  createdAt: string;
}

export interface AnalyticsSnapshot {
  visitors: number;
  inquiries: number;
  bookings: number;
  occupancyRate: number;
  revenue: number;
}

export interface Activity {
  id: ID;
  label: string;
  at: string;
}

export interface OpenRouterStatus {
  configured: boolean;
  model?: string;
  dailyUsage?: number;
  monthlyEstimate?: number;
  status: string;
}

export interface MissionControlData {
  todayArrivals: Booking[];
  todayDepartures: Booking[];
  currentGuests: Booking[];
  openInquiries: Inquiry[];
  pendingApprovals: Approval[];
  cleaningTasks: Task[];
  maintenanceTasks: Task[];
  aiChats: AIChat[];
  analytics: AnalyticsSnapshot;
  openRouter: OpenRouterStatus;
  recentBookings: Booking[];
  buildStatus: string;
  recentActivity: Activity[];
}
