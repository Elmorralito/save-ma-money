import { z } from "zod";

import {
  ACCOUNT_KIND_SLUGS,
  LEDGER_SIDE_SLUGS,
  extensionFieldForAccountKind,
} from "@/lib/accountKinds";

const optionalNumberString = z
  .string()
  .refine((value) => value.trim() === "" || Number.isFinite(Number(value)), {
    message: "Must be a valid number",
  });

const requiredNumberString = (label: string) =>
  z
    .string()
    .trim()
    .min(1, `${label} is required`)
    .refine((value) => Number.isFinite(Number(value)), { message: `${label} must be a number` });

/** UX schema for {@link AccountFormState} — OpenAPI-aligned shape checks only. */
export const accountFormSchema = z
  .object({
    name: z.string().trim().min(1, "Name is required").max(255),
    description: z.string(),
    account_kind: z.enum(ACCOUNT_KIND_SLUGS),
    ledger_side: z.enum(LEDGER_SIDE_SLUGS),
    currency: z
      .string()
      .trim()
      .length(3, "Currency must be a 3-letter code")
      .regex(/^[A-Za-z]{3}$/, "Currency must be a 3-letter code"),
    initial_value: optionalNumberString,
    banking_entity: z.string(),
    banking_account_number: z.string(),
    trading_buy_value: z.string(),
    trading_units: z.string(),
    re_address: z.string(),
    re_city: z.string(),
    re_country: z.string(),
    re_total_area: z.string(),
    re_built_area: z.string(),
    re_area_unit: z.string(),
    re_ownership: z.string(),
    re_participation: z.string(),
    credit_limit: z.string(),
    loan_is_paid_off: z.boolean(),
    loan_insurance_payment: z.string(),
    loan_extras_payment: z.string(),
    is_active: z.boolean(),
  })
  .superRefine((state, ctx) => {
    const extension = extensionFieldForAccountKind(state.account_kind);
    if (extension === "banking_details") {
      if (state.banking_entity.trim() === "") {
        ctx.addIssue({
          code: "custom",
          path: ["banking_entity"],
          message: "Entity is required",
        });
      }
    }
    if (extension === "trading_details") {
      const buy = requiredNumberString("Buy value").safeParse(state.trading_buy_value);
      if (!buy.success) {
        ctx.addIssue({
          code: "custom",
          path: ["trading_buy_value"],
          message: buy.error.issues[0]?.message ?? "Buy value is required",
        });
      }
      const units = requiredNumberString("Units").safeParse(state.trading_units);
      if (!units.success) {
        ctx.addIssue({
          code: "custom",
          path: ["trading_units"],
          message: units.error.issues[0]?.message ?? "Units is required",
        });
      }
    }
    if (extension === "credit_card_details") {
      const limit = requiredNumberString("Credit limit").safeParse(state.credit_limit);
      if (!limit.success) {
        ctx.addIssue({
          code: "custom",
          path: ["credit_limit"],
          message: limit.error.issues[0]?.message ?? "Credit limit is required",
        });
      }
    }
    if (extension === "loan_details") {
      const insurance = requiredNumberString("Insurance payment").safeParse(
        state.loan_insurance_payment,
      );
      if (!insurance.success) {
        ctx.addIssue({
          code: "custom",
          path: ["loan_insurance_payment"],
          message: insurance.error.issues[0]?.message ?? "Insurance payment is required",
        });
      }
      const extras = requiredNumberString("Extras payment").safeParse(state.loan_extras_payment);
      if (!extras.success) {
        ctx.addIssue({
          code: "custom",
          path: ["loan_extras_payment"],
          message: extras.error.issues[0]?.message ?? "Extras payment is required",
        });
      }
    }
    if (extension === "real_estate_details") {
      if (state.re_address.trim() === "") {
        ctx.addIssue({ code: "custom", path: ["re_address"], message: "Address is required" });
      }
      if (state.re_city.trim() === "") {
        ctx.addIssue({ code: "custom", path: ["re_city"], message: "City is required" });
      }
      if (state.re_country.trim() === "") {
        ctx.addIssue({ code: "custom", path: ["re_country"], message: "Country is required" });
      }
      for (const [key, label] of [
        ["re_total_area", "Total area"],
        ["re_built_area", "Built area"],
        ["re_participation", "Participation"],
      ] as const) {
        const parsed = requiredNumberString(label).safeParse(state[key]);
        if (!parsed.success) {
          ctx.addIssue({
            code: "custom",
            path: [key],
            message: parsed.error.issues[0]?.message ?? `${label} is required`,
          });
        }
      }
    }
  });

export type AccountFormSchema = z.infer<typeof accountFormSchema>;
