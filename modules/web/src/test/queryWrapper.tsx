import { QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement, ReactNode } from "react";

import { createTestQueryClient } from "@/test/createTestQueryClient";

export function QueryTestProvider({
  children,
  client = createTestQueryClient(),
}: {
  children: ReactNode;
  client?: ReturnType<typeof createTestQueryClient>;
}): ReactElement {
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
