export interface PendingTask {
  taskId: string;
  status: string;
}

export type PendingTasksMap = Record<string, PendingTask>;
