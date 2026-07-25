export function formatError(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  if (typeof error === 'string') {
    return error;
  }

  if (error && typeof error === 'object') {
    const record = error as Record<string, unknown>;

    if (typeof record.message === 'string' && record.message.trim()) {
      return record.message;
    }

    const entries = Object.entries(record);
    if (entries.length === 1) {
      const [kind, value] = entries[0];
      if (typeof value === 'string') {
        return `${kind}: ${value}`;
      }
      if (value !== null && value !== undefined) {
        return `${kind}: ${JSON.stringify(value)}`;
      }
    }

    try {
      return JSON.stringify(error);
    } catch {
      return 'Unexpected error';
    }
  }

  return 'Unexpected error';
}
