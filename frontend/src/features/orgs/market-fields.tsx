"use client";

import { Lock } from "lucide-react";

import { Field } from "@/components/forms/field";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";

import type { AIEngine, Entitlements, MarketIn, SearchEngine } from "./api";
import { AI_ENGINES, SEARCH_ENGINES } from "./engines";

export const DEFAULT_MARKET: MarketIn = {
  country: "US",
  language: "en",
  location: null,
  device: "desktop",
  search_engines: ["google"],
  ai_engines: [],
};

/** Client-side mirror of the API's market validation (the API re-validates). */
export function marketErrors(market: MarketIn): Partial<Record<keyof MarketIn, string>> {
  const errors: Partial<Record<keyof MarketIn, string>> = {};
  if (!/^[A-Za-z]{2}$/.test(market.country)) errors.country = "Use a 2-letter country code.";
  if (!/^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$/.test(market.language))
    errors.language = "Use a language code such as en or pt-BR.";
  if (market.search_engines.length === 0) errors.search_engines = "Pick at least one engine.";
  return errors;
}

function toggle<T>(list: T[], item: T, on: boolean): T[] {
  return on ? [...new Set([...list, item])] : list.filter((x) => x !== item);
}

/**
 * Market editor: country, language, optional city, device, and the engines to track.
 * Engines the plan doesn't include are shown locked (never hidden) so users know the
 * add-on exists.
 */
export function MarketFields({
  idPrefix,
  value,
  onChange,
  entitlements,
}: {
  idPrefix: string;
  value: MarketIn;
  onChange: (next: MarketIn) => void;
  entitlements: Entitlements | undefined;
}) {
  const errors = marketErrors(value);
  const allowedSearch = new Set<SearchEngine>(entitlements?.search_engines ?? ["google"]);
  const allowedAi = new Set<AIEngine>(entitlements?.ai_engines ?? []);
  const set = (patch: Partial<MarketIn>) => onChange({ ...value, ...patch });

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        <Field id={`${idPrefix}-country`} label="Country" error={errors.country}>
          <Input
            id={`${idPrefix}-country`}
            value={value.country}
            maxLength={2}
            onChange={(e) => set({ country: e.target.value.toUpperCase() })}
          />
        </Field>
        <Field id={`${idPrefix}-language`} label="Language" error={errors.language}>
          <Input
            id={`${idPrefix}-language`}
            value={value.language}
            maxLength={20}
            onChange={(e) => set({ language: e.target.value })}
          />
        </Field>
        <Field id={`${idPrefix}-device`} label="Device">
          <NativeSelect
            id={`${idPrefix}-device`}
            value={value.device}
            onChange={(e) => set({ device: e.target.value as MarketIn["device"] })}
          >
            <option value="desktop">Desktop</option>
            <option value="mobile">Mobile</option>
          </NativeSelect>
        </Field>
      </div>
      <Field
        id={`${idPrefix}-location`}
        label="City or region (optional)"
        hint="For local results."
      >
        <Input
          id={`${idPrefix}-location`}
          value={value.location ?? ""}
          maxLength={200}
          onChange={(e) => set({ location: e.target.value.trim() ? e.target.value : null })}
        />
      </Field>

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">Search engines</legend>
        {errors.search_engines ? (
          <p role="alert" className="text-destructive text-sm">
            {errors.search_engines}
          </p>
        ) : null}
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {SEARCH_ENGINES.map(({ id, label }) => {
            const allowed = allowedSearch.has(id);
            return (
              <label
                key={id}
                className="flex items-center gap-2 text-sm aria-disabled:opacity-60"
                aria-disabled={!allowed}
              >
                <input
                  type="checkbox"
                  checked={value.search_engines.includes(id)}
                  disabled={!allowed}
                  onChange={(e) =>
                    set({ search_engines: toggle(value.search_engines, id, e.target.checked) })
                  }
                />
                {label}
                {!allowed ? <Lock className="h-3 w-3" aria-label="Not in your plan" /> : null}
              </label>
            );
          })}
        </div>
      </fieldset>

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">AI answer engines</legend>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {AI_ENGINES.map(({ id, label }) => {
            const allowed = allowedAi.has(id);
            return (
              <label
                key={id}
                className="flex items-center gap-2 text-sm aria-disabled:opacity-60"
                aria-disabled={!allowed}
              >
                <input
                  type="checkbox"
                  checked={(value.ai_engines ?? []).includes(id)}
                  disabled={!allowed}
                  onChange={(e) =>
                    set({ ai_engines: toggle(value.ai_engines ?? [], id, e.target.checked) })
                  }
                />
                {label}
                {!allowed ? <Lock className="h-3 w-3" aria-label="Not in your plan" /> : null}
              </label>
            );
          })}
        </div>
      </fieldset>
    </div>
  );
}
