"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell } from "lucide-react";
import Link from "next/link";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

import { reportKeys, reportsApi, type NotificationList } from "./api";

const POLL_MS = 60_000;

/** Live notifications: SSE stream with a polling fallback (cookie auth, same origin). */
export function useNotifications(orgId: string) {
  const queryClient = useQueryClient();
  const key = reportKeys.notifications(orgId);
  const query = useQuery({
    queryKey: key,
    queryFn: () => reportsApi.notifications(orgId),
    refetchInterval: POLL_MS,
  });
  useEffect(() => {
    if (typeof EventSource === "undefined") return;
    const source = new EventSource(`/api/v1/orgs/${orgId}/notifications/stream`);
    source.addEventListener("notifications", (event) => {
      try {
        queryClient.setQueryData(
          reportKeys.notifications(orgId),
          JSON.parse((event as MessageEvent<string>).data) as NotificationList,
        );
      } catch {
        // Ignore malformed frames; polling corrects the state.
      }
    });
    // The browser reconnects on its own after the server closes the stream.
    return () => source.close();
  }, [orgId, queryClient]);
  return { query, key };
}

export function NotificationBell({ orgId }: { orgId: string }) {
  const queryClient = useQueryClient();
  const { query, key } = useNotifications(orgId);
  const unread = query.data?.unread ?? 0;

  async function open(id: string) {
    await reportsApi.markRead(orgId, id);
    await queryClient.invalidateQueries({ queryKey: key });
  }

  async function readAll() {
    await reportsApi.markAllRead(orgId);
    await queryClient.invalidateQueries({ queryKey: key });
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"}
          className="relative"
        >
          <Bell className="h-4 w-4" aria-hidden />
          {unread ? (
            <span className="bg-destructive text-destructive-foreground absolute -top-0.5 -right-0.5 rounded-full px-1 text-[10px]">
              {unread > 99 ? "99+" : unread}
            </span>
          ) : null}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel className="flex items-center justify-between">
          <span>Notifications</span>
          {unread ? (
            <button type="button" className="text-xs underline" onClick={() => void readAll()}>
              Mark all read
            </button>
          ) : null}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {query.data && query.data.items.length > 0 ? (
          query.data.items.slice(0, 10).map((n) => (
            <DropdownMenuItem key={n.id} asChild onSelect={() => void open(n.id)}>
              <Link href={n.link ?? `/orgs/${orgId}`} className="block">
                <span className={n.read_at ? "text-muted-foreground" : "font-medium"}>
                  {n.title}
                </span>
                <span className="text-muted-foreground block text-xs">
                  {new Date(n.created_at).toLocaleString()}
                </span>
              </Link>
            </DropdownMenuItem>
          ))
        ) : (
          <p className="text-muted-foreground px-2 py-3 text-sm">
            No notifications. Turn on alerts from a project&apos;s dashboard.
          </p>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
