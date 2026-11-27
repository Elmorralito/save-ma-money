import { bffOAuthStartUrl, type BffOAuthProvider } from "@/api/auth";
import { Button } from "@/components/ui/button";

type OAuthProviderButtonsProps = {
  /** Relative SPA path after successful OAuth (default `/dashboard`). */
  returnTo?: string;
};

const PROVIDERS: {
  id: BffOAuthProvider;
  label: string;
  favicon: string;
}[] = [
  {
    id: "google",
    label: "Continue with Google",
    favicon: "/brand/google.ico",
  },
];

/**
 * Primary Google OAuth button that navigates to same-origin OAuth start (no JWT in JS).
 */
export function OAuthProviderButtons({ returnTo = "/dashboard" }: OAuthProviderButtonsProps) {
  function start(provider: BffOAuthProvider) {
    window.location.assign(bffOAuthStartUrl(provider, returnTo));
  }

  return (
    <div className="space-y-3">
      {PROVIDERS.map((provider) => (
        <Button
          key={provider.id}
          type="button"
          size="lg"
          className="h-11 w-full gap-2.5 shadow-sm"
          onClick={() => {
            start(provider.id);
          }}
        >
          <span className="flex size-5 items-center justify-center rounded-full bg-white p-0.5">
            <img
              src={provider.favicon}
              alt=""
              width={16}
              height={16}
              className="size-3.5 shrink-0"
              decoding="async"
            />
          </span>
          <span>{provider.label}</span>
        </Button>
      ))}
    </div>
  );
}
