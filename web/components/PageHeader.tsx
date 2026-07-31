/** Page title, optional subtitle and context chips — mirrors the Streamlit component. */
export function PageHeader({
  title,
  subtitle,
  chips = [],
}: {
  title: string;
  subtitle?: string;
  chips?: string[];
}) {
  return (
    <header className="mb-8">
      <h1 className="text-3xl font-extrabold sm:text-4xl">{title}</h1>
      {subtitle ? <p className="mt-2 max-w-2xl text-ink-soft">{subtitle}</p> : null}
      {chips.length > 0 ? (
        <ul className="mt-4 flex flex-wrap gap-2">
          {chips.map((chip) => (
            <li
              key={chip}
              className="rounded-full border border-line-soft bg-tile px-3 py-1 text-xs font-medium text-ink-muted"
            >
              {chip}
            </li>
          ))}
        </ul>
      ) : null}
    </header>
  );
}
