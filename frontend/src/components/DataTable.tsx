type Props = {
  rows: Record<string, unknown>[];
  columns?: string[];
  emptyText?: string;
};

export function DataTable({ rows, columns, emptyText = "暂无数据" }: Props) {
  const visibleColumns = columns ?? Object.keys(rows[0] ?? {});
  if (!rows.length) {
    return <div className="empty-table">{emptyText}</div>;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {visibleColumns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 200).map((row, index) => (
            <tr key={index}>
              {visibleColumns.map((column) => (
                <td key={column}>{formatCell(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "number") return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2);
  return String(value);
}
