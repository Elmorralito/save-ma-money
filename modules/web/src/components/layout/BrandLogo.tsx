import { cn } from "@/lib/utils";

type BrandLogoProps = {
  title: string;
  className?: string;
  imageClassName?: string;
};

/** Shared app identity shown in public and authenticated headers. */
export function BrandLogo({ title, className, imageClassName }: BrandLogoProps) {
  return (
    <div className={cn("flex min-w-0 items-center gap-2", className)}>
      <img
        src="/favicon-32.png"
        alt=""
        width={32}
        height={32}
        className={cn("size-8 shrink-0 rounded-md object-cover", imageClassName)}
      />
      <span className="truncate text-sm font-semibold tracking-tight">{title}</span>
    </div>
  );
}
