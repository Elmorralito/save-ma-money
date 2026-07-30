type StubPageProps = {
  title: string;
  description?: string;
};

/** Placeholder feature page until PPT-052+ wires real screens. */
export function StubPage({ title, description }: StubPageProps) {
  return (
    <div className="mx-auto w-full max-w-3xl space-y-2">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="text-sm text-muted-foreground">
        {description ?? "Feature UI lands in a later epic child. Navigation shell only for now."}
      </p>
    </div>
  );
}
