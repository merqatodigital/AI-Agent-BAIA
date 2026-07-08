import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { serverEnv, clientEnv } from "../config";
import type {
  Activity,
  Approval,
  ApprovalStatus,
  BlogPost,
  Booking,
  BookingStatus,
  Inquiry,
  InquiryStatus,
  MissionControlData,
  ResortProfile,
  Task,
} from "../types";
import type { DataStore } from "./store";

/**
 * Supabase-backed DataStore. Activated only when env vars are present.
 * Tables are referenced by name; the SQL schema is provided in
 * /supabase/schema.sql so a resort can provision its own project.
 */
export class SupabaseDataStore implements DataStore {
  private sb: SupabaseClient;

  constructor(url: string, key: string) {
    this.sb = createClient(url, key, {
      auth: { persistSession: false },
    });
  }

  async getResortProfile(resortId: string): Promise<ResortProfile> {
    const { data, error } = await this.sb
      .from("resort_profile")
      .select("*")
      .eq("id", resortId)
      .single();
    if (error) throw new Error(error.message);
    return data as ResortProfile;
  }

  async updateResortProfile(
    resortId: string,
    patch: Partial<ResortProfile>,
  ): Promise<ResortProfile> {
    const { data, error } = await this.sb
      .from("resort_profile")
      .update(patch)
      .eq("id", resortId)
      .select()
      .single();
    if (error) throw new Error(error.message);
    return data as ResortProfile;
  }

  async listInquiries(resortId: string): Promise<Inquiry[]> {
    return this.list("inquiries", resortId) as Promise<Inquiry[]>;
  }

  async createInquiry(
    resortId: string,
    input: Omit<Inquiry, "id" | "createdAt" | "status">,
  ): Promise<Inquiry> {
    const { data, error } = await this.sb
      .from("inquiries")
      .insert({ ...input, resortId, status: "new" as InquiryStatus })
      .select()
      .single();
    if (error) throw new Error(error.message);
    return data as Inquiry;
  }

  async updateInquiry(
    resortId: string,
    id: string,
    patch: Partial<Inquiry>,
  ): Promise<Inquiry> {
    const { data, error } = await this.sb
      .from("inquiries")
      .update(patch)
      .eq("id", id)
      .eq("resortId", resortId)
      .select()
      .single();
    if (error) throw new Error(error.message);
    return data as Inquiry;
  }

  async listBookings(resortId: string): Promise<Booking[]> {
    return this.list("bookings", resortId) as Promise<Booking[]>;
  }

  async createBooking(
    resortId: string,
    input: Omit<Booking, "id" | "createdAt" | "status"> & {
      status?: BookingStatus;
    },
  ): Promise<Booking> {
    const { data, error } = await this.sb
      .from("bookings")
      .insert({
        ...input,
        resortId,
        status: input.status ?? ("pending" as BookingStatus),
      })
      .select()
      .single();
    if (error) throw new Error(error.message);
    return data as Booking;
  }

  async listTasks(resortId: string): Promise<Task[]> {
    return this.list("tasks", resortId) as Promise<Task[]>;
  }

  async createTask(
    resortId: string,
    input: Omit<Task, "id" | "createdAt">,
  ): Promise<Task> {
    const { data, error } = await this.sb
      .from("tasks")
      .insert({ ...input, resortId })
      .select()
      .single();
    if (error) throw new Error(error.message);
    return data as Task;
  }

  async updateTask(
    resortId: string,
    id: string,
    patch: Partial<Task>,
  ): Promise<Task> {
    const { data, error } = await this.sb
      .from("tasks")
      .update(patch)
      .eq("id", id)
      .eq("resortId", resortId)
      .select()
      .single();
    if (error) throw new Error(error.message);
    return data as Task;
  }

  async listApprovals(resortId: string): Promise<Approval[]> {
    return this.list("approvals", resortId) as Promise<Approval[]>;
  }

  async createApproval(
    resortId: string,
    input: Omit<Approval, "id" | "createdAt" | "status"> & {
      status?: ApprovalStatus;
    },
  ): Promise<Approval> {
    const { data, error } = await this.sb
      .from("approvals")
      .insert({
        ...input,
        resortId,
        status: input.status ?? ("pending" as ApprovalStatus),
      })
      .select()
      .single();
    if (error) throw new Error(error.message);
    return data as Approval;
  }

  async updateApproval(
    resortId: string,
    id: string,
    patch: Partial<Approval>,
  ): Promise<Approval> {
    const { data, error } = await this.sb
      .from("approvals")
      .update(patch)
      .eq("id", id)
      .eq("resortId", resortId)
      .select()
      .single();
    if (error) throw new Error(error.message);
    return data as Approval;
  }

  async listBlogPosts(resortId: string): Promise<BlogPost[]> {
    return this.list("blog_posts", resortId) as Promise<BlogPost[]>;
  }

  async getMissionControl(resortId: string): Promise<MissionControlData> {
    const [bookings, inquiries, tasks, approvals, aiChats] =
      await Promise.all([
        this.listBookings(resortId),
        this.listInquiries(resortId),
        this.listTasks(resortId),
        this.listApprovals(resortId),
        this.sb
          .from("ai_chats")
          .select("*")
          .eq("resortId", resortId)
          .order("createdAt", { ascending: false })
          .limit(10),
      ]);

    const today = new Date().toISOString().slice(0, 10);
    const isBetween = (b: Booking) =>
      b.checkIn <= today && b.checkOut >= today;

    return {
      todayArrivals: bookings.filter((b) => b.checkIn === today),
      todayDepartures: bookings.filter((b) => b.checkOut === today),
      currentGuests: bookings.filter(
        (b) => isBetween(b) && b.status !== "cancelled",
      ),
      openInquiries: inquiries.filter((i) => i.status === "new"),
      pendingApprovals: approvals.filter((a) => a.status === "pending"),
      cleaningTasks: tasks.filter((t) => t.type === "housekeeping"),
      maintenanceTasks: tasks.filter((t) => t.type === "maintenance"),
      aiChats: (aiChats.data ?? []) as MissionControlData["aiChats"],
      analytics: {
        visitors: 0,
        inquiries: inquiries.length,
        bookings: bookings.filter((b) => b.status !== "cancelled").length,
        occupancyRate: 0,
        revenue: 0,
      },
      openRouter: {
        configured: false,
        status: "Connect an OpenRouter key in Admin.",
      },
      recentBookings: bookings.slice(0, 5),
      buildStatus: "ok",
      recentActivity: [] as Activity[],
    };
  }

  private async list<T>(table: string, resortId: string): Promise<T[]> {
    const { data, error } = await this.sb
      .from(table)
      .select("*")
      .eq("resortId", resortId)
      .order("createdAt", { ascending: false });
    if (error) throw new Error(error.message);
    return (data ?? []) as T[];
  }
}

/** Builds the right store for the current environment. */
export function createSupabaseStore(): DataStore {
  const url = serverEnv.supabaseUrl || clientEnv.supabaseUrl;
  const key =
    serverEnv.supabaseServiceRole ||
    serverEnv.supabaseAnonKey ||
    clientEnv.supabaseAnonKey;
  return new SupabaseDataStore(url, key);
}
