import type {
  Activity,
  Approval,
  ApprovalStatus,
  BlogPost,
  Booking,
  BookingStatus,
  Inquiry,
  MissionControlData,
  ResortProfile,
  Task,
} from "../types";
import type { DataStore } from "./store";

/**
 * In-memory adapter with realistic seeded demo data so the entire product
 * (landing, Mission Control, admin) runs with ZERO external configuration.
 *
 * This is NOT production storage — it is clearly-labeled seed data that lets
 * the app boot and be exercised end-to-end. Swap in SupabaseDataStore (or any
 * DataStore implementation) by setting NEXT_PUBLIC_SUPABASE_URL.
 */

let idCounter = 1000;
const nextId = (p: string) => `${p}_${(++idCounter).toString(36)}`;

function daysFromNow(d: number): string {
  const dt = new Date();
  dt.setDate(dt.getDate() + d);
  return dt.toISOString().slice(0, 10);
}

const today = daysFromNow(0);

const seedProfile: ResortProfile = {
  id: "resort_demo",
  name: "Kapwa Bay Resort",
  tagline: "Where strangers become friends.",
  description:
    "A boutique coastal retreat on the edge of Palawan. Natural materials, quiet luxury, and an AI concierge that knows your stay.",
  location: "San Vicente, Palawan, Philippines",
  heroImageUrl:
    "https://images.unsplash.com/photo-1505228395891-9a51e7e86bf6?auto=format&fit=crop&w=1600&q=80",
  contactEmail: "stay@kapwabay.example",
  contactPhone: "+63 967 206 2327",
  amenities: [
    "Infinity Pool",
    "Private Beach",
    "Spa & Wellness",
    "Farm-to-Table Restaurant",
    "Free WiFi",
    "Airport Transfer",
  ],
  policies:
    "Check-in 14:00 · Check-out 11:00 · Cancellations free up to 48h before arrival · No smoking indoors · Pets welcome on request.",
  faqs: [
    {
      id: "faq_1",
      question: "How do I get there from the airport?",
      answer:
        "We offer private transfers from San Vicente Airport (12 km). Book via the concierge and we'll confirm with you.",
    },
    {
      id: "faq_2",
      question: "Is breakfast included?",
      answer:
        "Yes — a farm-to-table breakfast is included for all villa bookings.",
    },
    {
      id: "faq_3",
      question: "Can the AI concierge book tours?",
      answer:
        "The concierge can recommend and request tours. Booking confirmations always go through a human for your safety.",
    },
  ],
  rooms: [
    {
      id: "room_garden",
      name: "Garden Villa",
      description: "Ground-floor villa opening onto tropical gardens.",
      pricePerNight: 120,
      capacity: 2,
      imageUrl:
        "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=900&q=80",
    },
    {
      id: "room_beach",
      name: "Beachfront Suite",
      description: "Steps from the sand with an ocean-facing terrace.",
      pricePerNight: 210,
      capacity: 3,
      imageUrl:
        "https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=900&q=80",
    },
  ],
  tours: [
    {
      id: "tour_island",
      name: "Island Hopping",
      description: "Half-day boat tour to hidden coves.",
      duration: "4 hours",
      price: 65,
    },
    {
      id: "tour_reef",
      name: "Reef Snorkel",
      description: "Guided snorkel on the house reef.",
      duration: "2 hours",
      price: 35,
    },
  ],
  restaurants: [
    {
      id: "rest_terra",
      name: "Terra",
      cuisine: "Filipino farm-to-table",
      hours: "07:00 – 22:00",
    },
  ],
  transport: {
    airport: "San Vicente Airport (SWL)",
    airportDistanceKm: 12,
    notes: "Private transfer available on request via concierge.",
  },
  emergencyContacts: [
    { id: "em_1", label: "Front Desk", phone: "+63 967 206 2327" },
    { id: "em_2", label: "Medical (Bernardino)", phone: "+63 900 000 0000" },
  ],
};

const seedInquiries: Inquiry[] = [
  {
    id: "inq_1",
    name: "Ana Reyes",
    email: "ana@example.com",
    message: "Do you have availability for 2 guests next week?",
    checkIn: daysFromNow(3),
    checkOut: daysFromNow(6),
    guests: 2,
    status: "new",
    createdAt: daysFromNow(-1),
  },
];

const seedBookings: Booking[] = [
  {
    id: "bk_1",
    guestName: "Liam Carter",
    roomId: "room_beach",
    checkIn: daysFromNow(-1),
    checkOut: daysFromNow(3),
    guests: 2,
    status: "confirmed",
    createdAt: daysFromNow(-8),
  },
  {
    id: "bk_2",
    guestName: "Mei Tan",
    roomId: "room_garden",
    checkIn: today,
    checkOut: daysFromNow(4),
    guests: 2,
    status: "confirmed",
    createdAt: daysFromNow(-10),
  },
  {
    id: "bk_3",
    guestName: "Tom Becker",
    roomId: "room_garden",
    checkIn: daysFromNow(2),
    checkOut: daysFromNow(5),
    guests: 3,
    status: "pending",
    createdAt: daysFromNow(-2),
  },
];

const seedTasks: Task[] = [
  {
    id: "task_1",
    type: "housekeeping",
    title: "Turnover Garden Villa",
    description: "Full clean before Mei Tan arrival.",
    status: "done",
    assignee: "Joy",
    due: daysFromNow(-1),
    createdAt: daysFromNow(-2),
  },
  {
    id: "task_2",
    type: "housekeeping",
    title: "Refresh Beachfront Suite linens",
    status: "in_progress",
    assignee: "Joy",
    due: today,
    createdAt: daysFromNow(-1),
  },
  {
    id: "task_3",
    type: "maintenance",
    title: "Pool pump noise",
    description: "Investigate hum from north pump.",
    status: "todo",
    assignee: "Marco",
    due: daysFromNow(1),
    createdAt: daysFromNow(0),
  },
];

const seedApprovals: Approval[] = [
  {
    id: "ap_1",
    action: "Publish Instagram post",
    description: "Concierge drafted a post about the new reef tour.",
    requestedBy: "Marketing Agent",
    status: "pending",
    createdAt: daysFromNow(0),
  },
  {
    id: "ap_2",
    action: "Adjust pricing +12% (peak season)",
    description: "Revenue Agent suggests raising Beachfront Suite rate.",
    requestedBy: "Revenue Agent",
    status: "pending",
    createdAt: daysFromNow(-1),
  },
];

const seedBlog: BlogPost[] = [
  {
    id: "blog_1",
    title: "A Slow Morning on the Reef",
    slug: "slow-morning-on-the-reef",
    excerpt: "Why our guests start the day in the water.",
    body: "Sunrise at Kapwa Bay is best experienced from the reef...",
    published: true,
    createdAt: daysFromNow(-4),
  },
];

export class DevDataStore implements DataStore {
  private profile: ResortProfile = structuredClone(seedProfile);
  private inquiries: Inquiry[] = structuredClone(seedInquiries);
  private bookings: Booking[] = structuredClone(seedBookings);
  private tasks: Task[] = structuredClone(seedTasks);
  private approvals: Approval[] = structuredClone(seedApprovals);
  private blog: BlogPost[] = structuredClone(seedBlog);
  private activity: Activity[] = [
    { id: "a1", label: "Concierge answered 3 guest questions", at: daysFromNow(0) },
    { id: "a2", label: "New inquiry from Ana Reyes", at: daysFromNow(-1) },
  ];

  async getResortProfile(resortId: string): Promise<ResortProfile> {
    void resortId;
    return structuredClone(this.profile);
  }

  async updateResortProfile(
    resortId: string,
    patch: Partial<ResortProfile>,
  ): Promise<ResortProfile> {
    void resortId;
    this.profile = { ...this.profile, ...patch, id: this.profile.id };
    return structuredClone(this.profile);
  }

  async listInquiries(resortId: string): Promise<Inquiry[]> {
    void resortId;
    return structuredClone(this.inquiries);
  }

  async createInquiry(
    resortId: string,
    input: Omit<Inquiry, "id" | "createdAt" | "status">,
  ): Promise<Inquiry> {
    void resortId;
    const record: Inquiry = {
      ...input,
      id: nextId("inq"),
      status: "new",
      createdAt: new Date().toISOString(),
    };
    this.inquiries.unshift(record);
    this.activity.unshift({
      id: nextId("a"),
      label: `New inquiry from ${input.name}`,
      at: record.createdAt,
    });
    return structuredClone(record);
  }

  async updateInquiry(
    resortId: string,
    id: string,
    patch: Partial<Inquiry>,
  ): Promise<Inquiry> {
    void resortId;
    const idx = this.inquiries.findIndex((i) => i.id === id);
    if (idx === -1) throw new Error(`Inquiry ${id} not found`);
    this.inquiries[idx] = { ...this.inquiries[idx], ...patch };
    return structuredClone(this.inquiries[idx]);
  }

  async listBookings(resortId: string): Promise<Booking[]> {
    void resortId;
    return structuredClone(this.bookings);
  }

  async createBooking(
    resortId: string,
    input: Omit<Booking, "id" | "createdAt" | "status"> & {
      status?: BookingStatus;
    },
  ): Promise<Booking> {
    void resortId;
    const record: Booking = {
      ...input,
      id: nextId("bk"),
      status: input.status ?? "pending",
      createdAt: new Date().toISOString(),
    };
    this.bookings.unshift(record);
    return structuredClone(record);
  }

  async listTasks(resortId: string): Promise<Task[]> {
    void resortId;
    return structuredClone(this.tasks);
  }

  async createTask(
    resortId: string,
    input: Omit<Task, "id" | "createdAt">,
  ): Promise<Task> {
    void resortId;
    const record: Task = {
      ...input,
      id: nextId("task"),
      createdAt: new Date().toISOString(),
    };
    this.tasks.unshift(record);
    return structuredClone(record);
  }

  async updateTask(
    resortId: string,
    id: string,
    patch: Partial<Task>,
  ): Promise<Task> {
    void resortId;
    const idx = this.tasks.findIndex((t) => t.id === id);
    if (idx === -1) throw new Error(`Task ${id} not found`);
    this.tasks[idx] = { ...this.tasks[idx], ...patch };
    return structuredClone(this.tasks[idx]);
  }

  async listApprovals(resortId: string): Promise<Approval[]> {
    void resortId;
    return structuredClone(this.approvals);
  }

  async createApproval(
    resortId: string,
    input: Omit<Approval, "id" | "createdAt" | "status"> & {
      status?: ApprovalStatus;
    },
  ): Promise<Approval> {
    void resortId;
    const record: Approval = {
      ...input,
      id: nextId("ap"),
      status: input.status ?? "pending",
      createdAt: new Date().toISOString(),
    };
    this.approvals.unshift(record);
    return structuredClone(record);
  }

  async updateApproval(
    resortId: string,
    id: string,
    patch: Partial<Approval>,
  ): Promise<Approval> {
    void resortId;
    const idx = this.approvals.findIndex((a) => a.id === id);
    if (idx === -1) throw new Error(`Approval ${id} not found`);
    this.approvals[idx] = { ...this.approvals[idx], ...patch };
    return structuredClone(this.approvals[idx]);
  }

  async listBlogPosts(resortId: string): Promise<BlogPost[]> {
    void resortId;
    return structuredClone(this.blog);
  }

  async getMissionControl(resortId: string): Promise<MissionControlData> {
    const [bookings, inquiries, tasks, approvals] = await Promise.all([
      this.listBookings(resortId),
      this.listInquiries(resortId),
      this.listTasks(resortId),
      this.listApprovals(resortId),
    ]);

    const isBetween = (b: Booking) =>
      b.checkIn <= today && b.checkOut >= today;
    const todayArrivals = bookings.filter((b) => b.checkIn === today);
    const todayDepartures = bookings.filter((b) => b.checkOut === today);
    const currentGuests = bookings.filter(
      (b) => isBetween(b) && b.status !== "cancelled",
    );

    // Demo AI chats (in-memory only). Real adapter pulls from Supabase.
    const aiChats = [
      {
        id: "chat_1",
        guestName: "Liam Carter",
        message: "What time is breakfast?",
        response:
          "Breakfast at Terra is served 7:00–10:30. Would you like it delivered to your suite?",
        escalated: false,
        createdAt: daysFromNow(0),
      },
      {
        id: "chat_2",
        guestName: "Mei Tan",
        message: "Can you book the reef snorkel for tomorrow?",
        response:
          "I've flagged a Reef Snorkel request for tomorrow 9:00. A team member will confirm shortly.",
        escalated: true,
        createdAt: daysFromNow(0),
      },
    ];

    return {
      todayArrivals,
      todayDepartures,
      currentGuests,
      openInquiries: inquiries.filter((i) => i.status === "new"),
      pendingApprovals: approvals.filter((a) => a.status === "pending"),
      cleaningTasks: tasks.filter((t) => t.type === "housekeeping"),
      maintenanceTasks: tasks.filter((t) => t.type === "maintenance"),
      aiChats,
      analytics: {
        visitors: 1284,
        inquiries: inquiries.length,
        bookings: bookings.filter((b) => b.status !== "cancelled").length,
        occupancyRate: 0.72,
        revenue: 4820,
      },
      openRouter: {
        configured: false,
        status:
          "Demo mode — connect an OpenRouter key in Admin to enable the AI concierge.",
      },
      recentBookings: bookings.slice(0, 5),
      buildStatus: "ok",
      recentActivity: this.activity.slice(0, 6),
    };
  }
}
