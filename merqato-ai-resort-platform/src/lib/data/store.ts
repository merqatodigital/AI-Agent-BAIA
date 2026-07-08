import type {
  Approval,
  BlogPost,
  Booking,
  Inquiry,
  MissionControlData,
  ResortProfile,
  Task,
} from "../types";

/**
 * The single contract every storage backend implements. Swapping Supabase for
 * another DB means writing one new adapter — nothing else in the app changes.
 */
export interface DataStore {
  getResortProfile(resortId: string): Promise<ResortProfile>;
  updateResortProfile(
    resortId: string,
    patch: Partial<ResortProfile>,
  ): Promise<ResortProfile>;

  listInquiries(resortId: string): Promise<Inquiry[]>;
  createInquiry(
    resortId: string,
    input: Omit<Inquiry, "id" | "createdAt" | "status">,
  ): Promise<Inquiry>;
  updateInquiry(
    resortId: string,
    id: string,
    patch: Partial<Inquiry>,
  ): Promise<Inquiry>;

  listBookings(resortId: string): Promise<Booking[]>;
  createBooking(
    resortId: string,
    input: Omit<Booking, "id" | "createdAt" | "status"> & {
      status?: Booking["status"];
    },
  ): Promise<Booking>;

  listTasks(resortId: string): Promise<Task[]>;
  createTask(
    resortId: string,
    input: Omit<Task, "id" | "createdAt">,
  ): Promise<Task>;
  updateTask(
    resortId: string,
    id: string,
    patch: Partial<Task>,
  ): Promise<Task>;

  listApprovals(resortId: string): Promise<Approval[]>;
  createApproval(
    resortId: string,
    input: Omit<Approval, "id" | "createdAt" | "status"> & {
      status?: Approval["status"];
    },
  ): Promise<Approval>;
  updateApproval(
    resortId: string,
    id: string,
    patch: Partial<Approval>,
  ): Promise<Approval>;

  listBlogPosts(resortId: string): Promise<BlogPost[]>;

  getMissionControl(resortId: string): Promise<MissionControlData>;
}
