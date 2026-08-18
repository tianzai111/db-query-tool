/** Query result table component with pagination and export toolbar. */
import React, { useState } from "react";
import { Table, Tag, Space } from "antd";
import { QueryResult } from "../types/query";
import { ExportButtons } from "./ExportButtons";
import { exportResultClient, ExportFormat } from "../services/export";

interface ResultTableProps {
  result: QueryResult | null;
  loading?: boolean;
  /** Database name used to build the export filename. */
  databaseName?: string;
  /**
   * When true, an export toolbar is shown above the table. Defaults to true so
   * that any screen embedding this component gets CSV/JSON export for free.
   */
  showExport?: boolean;
}

export const ResultTable: React.FC<ResultTableProps> = ({
  result,
  loading = false,
  databaseName = "export",
  showExport = true,
}) => {
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 50,
  });

  if (!result) {
    return null;
  }

  const columns = result.columns.map((col) => ({
    title: col.name,
    dataIndex: col.name,
    key: col.name,
    render: (value: any) => {
      if (value === null || value === undefined) {
        return <Tag color="default">NULL</Tag>;
      }
      if (typeof value === "boolean") {
        return value ? "✓" : "✗";
      }
      if (value instanceof Date) {
        return value.toLocaleString();
      }
      return String(value);
    },
  }));

  const handleTableChange = (newPagination: any) => {
    setPagination({
      current: newPagination.current,
      pageSize: newPagination.pageSize,
    });
  };

  const handleExport = (format: ExportFormat) => {
    exportResultClient(result, format, databaseName);
  };

  return (
    <div>
      <div
        style={{
          marginBottom: 16,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        <Space wrap>
          <Tag color="blue">Rows: {result.rowCount}</Tag>
          <Tag color="green">Execution Time: {result.executionTimeMs}ms</Tag>
        </Space>
        {showExport && (
          <ExportButtons onExport={handleExport} disabled={result.rowCount === 0} />
        )}
      </div>
      <Table
        columns={columns}
        dataSource={result.rows.map((row, index) => ({
          ...row,
          key: index,
        }))}
        loading={loading}
        pagination={{
          current: pagination.current,
          pageSize: pagination.pageSize,
          total: result.rowCount,
          showSizeChanger: true,
          showTotal: (total) => `Total ${total} rows`,
          pageSizeOptions: ["10", "50", "100", "500"],
        }}
        onChange={handleTableChange}
        scroll={{ x: "max-content" }}
      />
    </div>
  );
};
