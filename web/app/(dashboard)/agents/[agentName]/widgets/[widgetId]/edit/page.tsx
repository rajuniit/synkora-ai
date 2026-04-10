"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";

export default function WidgetEditPage() {
  const params = useParams();
  const router = useRouter();

  useEffect(() => {
    router.replace(`/agents/${params.agentName}/widgets`);
  }, [params.agentName, router]);

  return null;
}
