import { call } from './frappe-sdk';

export interface TableCallRequest {
  name: string;
  table: string;
  request_type: 'Call Waiter' | 'Water' | 'Bill' | 'Cancel';
  waiter: string | null;
  requested_on: string;
}

export async function getOpenCallRequests(): Promise<TableCallRequest[]> {
  const res = await call.get<{ message: TableCallRequest[] }>(
    'ury.ury.api.table_call.get_open_call_requests'
  );
  return res.message;
}

export async function resolveCallRequest(name: string): Promise<void> {
  await call.post('ury.ury.api.table_call.resolve_call_request', { name });
}

export async function createManualCallRequest(
  table: string,
  requestType: TableCallRequest['request_type']
): Promise<void> {
  await call.post('ury.ury.api.table_call.create_manual_call_request', {
    table,
    request_type: requestType,
  });
}
