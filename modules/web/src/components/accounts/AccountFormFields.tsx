import {
  ACCOUNT_KIND_SLUGS,
  AREA_UNIT_SLUGS,
  extensionFieldForAccountKind,
  LEDGER_SIDE_SLUGS,
  OWNERSHIP_SLUGS,
  type AccountKindSlug,
} from "@/lib/accountKinds";
import {
  applyAccountKindChange,
  type AccountFormState,
} from "@/components/accounts/accountFormState";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";

type AccountFormFieldsProps = {
  value: AccountFormState;
  onChange: (next: AccountFormState) => void;
  /** When editing, account_kind / ledger_side are immutable on the API. */
  mode: "create" | "edit";
  idPrefix: string;
};

export function AccountFormFields({ value, onChange, mode, idPrefix }: AccountFormFieldsProps) {
  const extension = extensionFieldForAccountKind(value.account_kind);

  function patch(partial: Partial<AccountFormState>) {
    onChange({ ...value, ...partial });
  }

  return (
    <div className="grid max-h-[60vh] gap-3 overflow-y-auto pr-1">
      <div className="space-y-2">
        <Label htmlFor={`${idPrefix}-name`}>Name</Label>
        <Input
          id={`${idPrefix}-name`}
          required
          maxLength={255}
          value={value.name}
          onChange={(event) => {
            patch({ name: event.target.value });
          }}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor={`${idPrefix}-description`}>Description</Label>
        <Input
          id={`${idPrefix}-description`}
          value={value.description}
          onChange={(event) => {
            patch({ description: event.target.value });
          }}
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor={`${idPrefix}-kind`}>Account kind</Label>
          <NativeSelect
            id={`${idPrefix}-kind`}
            required
            disabled={mode === "edit"}
            value={value.account_kind}
            onChange={(event) => {
              onChange(applyAccountKindChange(value, event.target.value as AccountKindSlug));
            }}
          >
            {ACCOUNT_KIND_SLUGS.map((kind) => (
              <option key={kind} value={kind}>
                {kind}
              </option>
            ))}
          </NativeSelect>
        </div>
        <div className="space-y-2">
          <Label htmlFor={`${idPrefix}-ledger`}>Ledger side</Label>
          <NativeSelect
            id={`${idPrefix}-ledger`}
            required
            disabled={mode === "edit"}
            value={value.ledger_side}
            onChange={(event) => {
              patch({ ledger_side: event.target.value as AccountFormState["ledger_side"] });
            }}
          >
            {LEDGER_SIDE_SLUGS.map((side) => (
              <option key={side} value={side}>
                {side}
              </option>
            ))}
          </NativeSelect>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor={`${idPrefix}-currency`}>Currency</Label>
          <Input
            id={`${idPrefix}-currency`}
            required
            minLength={3}
            maxLength={3}
            value={value.currency}
            onChange={(event) => {
              patch({ currency: event.target.value.toUpperCase() });
            }}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor={`${idPrefix}-initial`}>Initial value</Label>
          <Input
            id={`${idPrefix}-initial`}
            type="number"
            min={0}
            step="any"
            value={value.initial_value}
            onChange={(event) => {
              patch({ initial_value: event.target.value });
            }}
          />
        </div>
      </div>

      {mode === "edit" ? (
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={value.is_active}
            onChange={(event) => {
              patch({ is_active: event.target.checked });
            }}
          />
          Active
        </label>
      ) : null}

      {extension === "banking_details" ? (
        <fieldset className="space-y-3 rounded-md border border-border p-3">
          <legend className="px-1 text-sm font-medium">Banking details</legend>
          <div className="space-y-2">
            <Label htmlFor={`${idPrefix}-entity`}>Entity</Label>
            <Input
              id={`${idPrefix}-entity`}
              required
              value={value.banking_entity}
              onChange={(event) => {
                patch({ banking_entity: event.target.value });
              }}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor={`${idPrefix}-acct-num`}>Account number</Label>
            <Input
              id={`${idPrefix}-acct-num`}
              value={value.banking_account_number}
              onChange={(event) => {
                patch({ banking_account_number: event.target.value });
              }}
            />
          </div>
        </fieldset>
      ) : null}

      {extension === "trading_details" ? (
        <fieldset className="space-y-3 rounded-md border border-border p-3">
          <legend className="px-1 text-sm font-medium">Trading details</legend>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor={`${idPrefix}-buy`}>Buy value</Label>
              <Input
                id={`${idPrefix}-buy`}
                type="number"
                min={0}
                step="any"
                required
                value={value.trading_buy_value}
                onChange={(event) => {
                  patch({ trading_buy_value: event.target.value });
                }}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor={`${idPrefix}-units`}>Units</Label>
              <Input
                id={`${idPrefix}-units`}
                type="number"
                min={1}
                step={1}
                required
                value={value.trading_units}
                onChange={(event) => {
                  patch({ trading_units: event.target.value });
                }}
              />
            </div>
          </div>
        </fieldset>
      ) : null}

      {extension === "credit_card_details" ? (
        <fieldset className="space-y-3 rounded-md border border-border p-3">
          <legend className="px-1 text-sm font-medium">Credit card details</legend>
          <div className="space-y-2">
            <Label htmlFor={`${idPrefix}-limit`}>Credit limit</Label>
            <Input
              id={`${idPrefix}-limit`}
              type="number"
              min={0}
              step="any"
              required
              value={value.credit_limit}
              onChange={(event) => {
                patch({ credit_limit: event.target.value });
              }}
            />
          </div>
        </fieldset>
      ) : null}

      {extension === "loan_details" ? (
        <fieldset className="space-y-3 rounded-md border border-border p-3">
          <legend className="px-1 text-sm font-medium">Loan details</legend>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={value.loan_is_paid_off}
              onChange={(event) => {
                patch({ loan_is_paid_off: event.target.checked });
              }}
            />
            Paid off
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor={`${idPrefix}-ins`}>Insurance payment</Label>
              <Input
                id={`${idPrefix}-ins`}
                type="number"
                min={0}
                step="any"
                value={value.loan_insurance_payment}
                onChange={(event) => {
                  patch({ loan_insurance_payment: event.target.value });
                }}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor={`${idPrefix}-extras`}>Extras payment</Label>
              <Input
                id={`${idPrefix}-extras`}
                type="number"
                min={0}
                step="any"
                value={value.loan_extras_payment}
                onChange={(event) => {
                  patch({ loan_extras_payment: event.target.value });
                }}
              />
            </div>
          </div>
        </fieldset>
      ) : null}

      {extension === "real_estate_details" ? (
        <fieldset className="space-y-3 rounded-md border border-border p-3">
          <legend className="px-1 text-sm font-medium">Real estate details</legend>
          <div className="space-y-2">
            <Label htmlFor={`${idPrefix}-address`}>Address</Label>
            <Input
              id={`${idPrefix}-address`}
              required
              value={value.re_address}
              onChange={(event) => {
                patch({ re_address: event.target.value });
              }}
            />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor={`${idPrefix}-city`}>City</Label>
              <Input
                id={`${idPrefix}-city`}
                required
                value={value.re_city}
                onChange={(event) => {
                  patch({ re_city: event.target.value });
                }}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor={`${idPrefix}-country`}>Country</Label>
              <Input
                id={`${idPrefix}-country`}
                required
                value={value.re_country}
                onChange={(event) => {
                  patch({ re_country: event.target.value });
                }}
              />
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor={`${idPrefix}-total`}>Total area</Label>
              <Input
                id={`${idPrefix}-total`}
                type="number"
                min={0}
                step="any"
                required
                value={value.re_total_area}
                onChange={(event) => {
                  patch({ re_total_area: event.target.value });
                }}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor={`${idPrefix}-built`}>Built area</Label>
              <Input
                id={`${idPrefix}-built`}
                type="number"
                min={0}
                step="any"
                required
                value={value.re_built_area}
                onChange={(event) => {
                  patch({ re_built_area: event.target.value });
                }}
              />
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor={`${idPrefix}-unit`}>Area unit</Label>
              <NativeSelect
                id={`${idPrefix}-unit`}
                value={value.re_area_unit}
                onChange={(event) => {
                  patch({ re_area_unit: event.target.value });
                }}
              >
                {AREA_UNIT_SLUGS.map((unit) => (
                  <option key={unit} value={unit}>
                    {unit}
                  </option>
                ))}
              </NativeSelect>
            </div>
            <div className="space-y-2">
              <Label htmlFor={`${idPrefix}-own`}>Ownership</Label>
              <NativeSelect
                id={`${idPrefix}-own`}
                value={value.re_ownership}
                onChange={(event) => {
                  patch({ re_ownership: event.target.value });
                }}
              >
                {OWNERSHIP_SLUGS.map((ownership) => (
                  <option key={ownership} value={ownership}>
                    {ownership}
                  </option>
                ))}
              </NativeSelect>
            </div>
            <div className="space-y-2">
              <Label htmlFor={`${idPrefix}-part`}>Participation</Label>
              <Input
                id={`${idPrefix}-part`}
                type="number"
                min={0}
                max={1}
                step="any"
                required
                value={value.re_participation}
                onChange={(event) => {
                  patch({ re_participation: event.target.value });
                }}
              />
            </div>
          </div>
        </fieldset>
      ) : null}
    </div>
  );
}
