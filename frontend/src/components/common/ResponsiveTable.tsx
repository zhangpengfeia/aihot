import { Table, type TableColumnType, type TableProps } from 'antd';
import type { ComponentPropsWithoutRef } from 'react';
import { useMobileLayout } from '../../hooks/useMobileLayout';

export type ResponsiveColumns<T> = (TableColumnType<T> & { mobileLabel?: string })[];

type CellProps = ComponentPropsWithoutRef<'td'> & { 'data-mobile-label'?: string };

function MobileValueCell({ 'data-mobile-label': label, children, ...props }: CellProps) {
  return (
    <td {...props} role="cell" data-mobile-label={label}>
      {label && <span className="mobile-table-label">{label}</span>}
      <div className="mobile-table-value">{children}</div>
    </td>
  );
}

const mobileTableComponents = {
  table: (props: ComponentPropsWithoutRef<'table'>) => <table {...props} role="table" />,
  body: {
    wrapper: (props: ComponentPropsWithoutRef<'tbody'>) => <tbody {...props} role="rowgroup" />,
    row: (props: ComponentPropsWithoutRef<'tr'>) => <tr {...props} role="row" />,
    cell: MobileValueCell,
  },
};

export function ResponsiveTable<T extends object>({
  className,
  columns,
  pagination,
  ...props
}: Omit<TableProps<T>, 'columns'> & { columns: ResponsiveColumns<T> }) {
  const mobile = useMobileLayout();
  if (!mobile) {
    return <Table<T> {...props} className={className} columns={columns} pagination={pagination} />;
  }

  const mobileColumns = columns.map(({ mobileLabel, ...column }) => ({
    ...column,
    fixed: undefined,
    width: undefined,
    onCell: (record: T, index?: number): CellProps => ({
      ...column.onCell?.(record, index),
      'data-mobile-label': mobileLabel ?? (typeof column.title === 'string' ? column.title : ''),
    }),
  }));

  return (
    <Table<T>
      {...props}
      className={className ? `mobile-table ${className}` : 'mobile-table'}
      columns={mobileColumns}
      components={mobileTableComponents}
      showHeader={false}
      scroll={undefined}
      pagination={pagination === false ? false : { ...pagination, showLessItems: true }}
    />
  );
}
