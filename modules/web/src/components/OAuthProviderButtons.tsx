import { bffOAuthStartUrl, type BffOAuthProvider } from "@/api/auth";
import { Button } from "@/components/ui/button";

type OAuthProviderButtonsProps = {
  /** Relative SPA path after successful BFF OAuth (default `/dashboard`). */
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
  {
    id: "github",
    label: "Continue with GitHub",
    favicon: "/brand/github.ico",
  },
];

/**
 * Google/GitHub buttons that navigate to BFF OAuth start (no JWT in JS).
 */
export function OAuthProviderButtons({ returnTo = "/dashboard" }: OAuthProviderButtonsProps) {
  function start(provider: BffOAuthProvider) {
    window.location.assign(bffOAuthStartUrl(provider, returnTo));
  }

  return (
    <div className="space-y-3">
      <p className="text-center text-xs text-muted-foreground">Or continue with</p>
      {PROVIDERS.map((provider) => (
        <Button
          key={provider.id}
          type="button"
          variant="outline"
          className="w-full"
          onClick={() => {
            start(provider.id);
          }}
        >
          <img
            src={provider.favicon}
            alt=""
            width={16}
            height={16}
            className="size-4 shrink-0"
            decoding="async"
          />
          {provider.label}
        </Button>
      ))}
    </div>
  );
}
