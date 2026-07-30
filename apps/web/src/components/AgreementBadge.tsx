export function AgreementBadge({ level }: { level: string }) {
  return (
    <span className={`badge badge-${level.replace(/ /g, "-")}`}>{level}</span>
  );
}
