import type { UseFormReturn } from "react-hook-form";

import type { AccountFormState } from "@/components/accounts/accountFormState";
import { FormField } from "@/forms/FormField";
import {
  ACCOUNT_KIND_SLUGS,
  AREA_UNIT_SLUGS,
  defaultLedgerSideForKind,
  extensionFieldForAccountKind,
  LEDGER_SIDE_SLUGS,
  OWNERSHIP_SLUGS,
  type AccountKindSlug,
} from "@/lib/accountKinds";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";

type AccountFormFieldsProps = {
  form: UseFormReturn<AccountFormState>;
  /** When editing, account_kind / ledger_side are immutable on the API. */
  mode: "create" | "edit";
  idPrefix: string;
};

export function AccountFormFields({ form, mode, idPrefix }: AccountFormFieldsProps) {
  const {
    register,
    watch,
    setValue,
    formState: { errors },
  } = form;
  const accountKind = watch("account_kind");
  const extension = extensionFieldForAccountKind(accountKind);

  return (
    <div className="grid max-h-[60vh] gap-3 overflow-y-auto pr-1">
      <FormField label="Name" htmlFor={`${idPrefix}-name`} error={errors.name?.message}>
        <Input id={`${idPrefix}-name`} maxLength={255} {...register("name")} />
      </FormField>

      <FormField
        label="Description"
        htmlFor={`${idPrefix}-description`}
        error={errors.description?.message}
      >
        <Input id={`${idPrefix}-description`} {...register("description")} />
      </FormField>

      <div className="grid gap-3 sm:grid-cols-2">
        <FormField
          label="Account kind"
          htmlFor={`${idPrefix}-kind`}
          error={errors.account_kind?.message}
        >
          <NativeSelect
            id={`${idPrefix}-kind`}
            disabled={mode === "edit"}
            {...register("account_kind", {
              onChange: (event) => {
                const kind = event.target.value as AccountKindSlug;
                setValue("account_kind", kind);
                setValue("ledger_side", defaultLedgerSideForKind(kind));
              },
            })}
          >
            {ACCOUNT_KIND_SLUGS.map((kind) => (
              <option key={kind} value={kind}>
                {kind}
              </option>
            ))}
          </NativeSelect>
        </FormField>
        <FormField
          label="Ledger side"
          htmlFor={`${idPrefix}-ledger`}
          error={errors.ledger_side?.message}
        >
          <NativeSelect
            id={`${idPrefix}-ledger`}
            disabled={mode === "edit"}
            {...register("ledger_side")}
          >
            {LEDGER_SIDE_SLUGS.map((side) => (
              <option key={side} value={side}>
                {side}
              </option>
            ))}
          </NativeSelect>
        </FormField>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <FormField
          label="Currency"
          htmlFor={`${idPrefix}-currency`}
          error={errors.currency?.message}
        >
          <Input
            id={`${idPrefix}-currency`}
            minLength={3}
            maxLength={3}
            {...register("currency", {
              onChange: (event) => {
                setValue("currency", event.target.value.toUpperCase());
              },
            })}
          />
        </FormField>
        <FormField
          label="Initial value"
          htmlFor={`${idPrefix}-initial`}
          error={errors.initial_value?.message}
        >
          <Input
            id={`${idPrefix}-initial`}
            type="number"
            min={0}
            step="any"
            {...register("initial_value")}
          />
        </FormField>
      </div>

      {mode === "edit" ? (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" {...register("is_active")} />
          Active
        </label>
      ) : null}

      {extension === "banking_details" ? (
        <fieldset className="space-y-3 rounded-md border border-border p-3">
          <legend className="px-1 text-sm font-medium">Banking details</legend>
          <FormField
            label="Entity"
            htmlFor={`${idPrefix}-entity`}
            error={errors.banking_entity?.message}
          >
            <Input id={`${idPrefix}-entity`} {...register("banking_entity")} />
          </FormField>
          <FormField
            label="Account number"
            htmlFor={`${idPrefix}-acct-num`}
            error={errors.banking_account_number?.message}
          >
            <Input id={`${idPrefix}-acct-num`} {...register("banking_account_number")} />
          </FormField>
        </fieldset>
      ) : null}

      {extension === "trading_details" ? (
        <fieldset className="space-y-3 rounded-md border border-border p-3">
          <legend className="px-1 text-sm font-medium">Trading details</legend>
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField
              label="Buy value"
              htmlFor={`${idPrefix}-buy`}
              error={errors.trading_buy_value?.message}
            >
              <Input
                id={`${idPrefix}-buy`}
                type="number"
                min={0}
                step="any"
                {...register("trading_buy_value")}
              />
            </FormField>
            <FormField
              label="Units"
              htmlFor={`${idPrefix}-units`}
              error={errors.trading_units?.message}
            >
              <Input
                id={`${idPrefix}-units`}
                type="number"
                min={1}
                step={1}
                {...register("trading_units")}
              />
            </FormField>
          </div>
        </fieldset>
      ) : null}

      {extension === "credit_card_details" ? (
        <fieldset className="space-y-3 rounded-md border border-border p-3">
          <legend className="px-1 text-sm font-medium">Credit card details</legend>
          <FormField
            label="Credit limit"
            htmlFor={`${idPrefix}-limit`}
            error={errors.credit_limit?.message}
          >
            <Input
              id={`${idPrefix}-limit`}
              type="number"
              min={0}
              step="any"
              {...register("credit_limit")}
            />
          </FormField>
        </fieldset>
      ) : null}

      {extension === "loan_details" ? (
        <fieldset className="space-y-3 rounded-md border border-border p-3">
          <legend className="px-1 text-sm font-medium">Loan details</legend>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" {...register("loan_is_paid_off")} />
            Paid off
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField
              label="Insurance payment"
              htmlFor={`${idPrefix}-ins`}
              error={errors.loan_insurance_payment?.message}
            >
              <Input
                id={`${idPrefix}-ins`}
                type="number"
                min={0}
                step="any"
                {...register("loan_insurance_payment")}
              />
            </FormField>
            <FormField
              label="Extras payment"
              htmlFor={`${idPrefix}-extras`}
              error={errors.loan_extras_payment?.message}
            >
              <Input
                id={`${idPrefix}-extras`}
                type="number"
                min={0}
                step="any"
                {...register("loan_extras_payment")}
              />
            </FormField>
          </div>
        </fieldset>
      ) : null}

      {extension === "real_estate_details" ? (
        <fieldset className="space-y-3 rounded-md border border-border p-3">
          <legend className="px-1 text-sm font-medium">Real estate details</legend>
          <FormField
            label="Address"
            htmlFor={`${idPrefix}-address`}
            error={errors.re_address?.message}
          >
            <Input id={`${idPrefix}-address`} {...register("re_address")} />
          </FormField>
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField label="City" htmlFor={`${idPrefix}-city`} error={errors.re_city?.message}>
              <Input id={`${idPrefix}-city`} {...register("re_city")} />
            </FormField>
            <FormField
              label="Country"
              htmlFor={`${idPrefix}-country`}
              error={errors.re_country?.message}
            >
              <Input id={`${idPrefix}-country`} {...register("re_country")} />
            </FormField>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField
              label="Total area"
              htmlFor={`${idPrefix}-total`}
              error={errors.re_total_area?.message}
            >
              <Input
                id={`${idPrefix}-total`}
                type="number"
                min={0}
                step="any"
                {...register("re_total_area")}
              />
            </FormField>
            <FormField
              label="Built area"
              htmlFor={`${idPrefix}-built`}
              error={errors.re_built_area?.message}
            >
              <Input
                id={`${idPrefix}-built`}
                type="number"
                min={0}
                step="any"
                {...register("re_built_area")}
              />
            </FormField>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <FormField
              label="Area unit"
              htmlFor={`${idPrefix}-unit`}
              error={errors.re_area_unit?.message}
            >
              <NativeSelect id={`${idPrefix}-unit`} {...register("re_area_unit")}>
                {AREA_UNIT_SLUGS.map((unit) => (
                  <option key={unit} value={unit}>
                    {unit}
                  </option>
                ))}
              </NativeSelect>
            </FormField>
            <FormField
              label="Ownership"
              htmlFor={`${idPrefix}-own`}
              error={errors.re_ownership?.message}
            >
              <NativeSelect id={`${idPrefix}-own`} {...register("re_ownership")}>
                {OWNERSHIP_SLUGS.map((ownership) => (
                  <option key={ownership} value={ownership}>
                    {ownership}
                  </option>
                ))}
              </NativeSelect>
            </FormField>
            <FormField
              label="Participation"
              htmlFor={`${idPrefix}-part`}
              error={errors.re_participation?.message}
            >
              <Input
                id={`${idPrefix}-part`}
                type="number"
                min={0}
                max={1}
                step="any"
                {...register("re_participation")}
              />
            </FormField>
          </div>
        </fieldset>
      ) : null}
    </div>
  );
}
