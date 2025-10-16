import { Box, Text, Button, Select, FormControl } from "@primer/react";
import { CheckCircleIcon, XCircleIcon, EyeIcon } from "@primer/octicons-react";

interface Record {
  id: number;
  output: string;
  status: string;
  metadata: any;
  trace?: Array<{
    block_type: string;
    input: any;
    output: any;
    accumulated_state?: any;
    error?: string;
  }>;
}

interface ValidationConfig {
  field_order: {
    primary: string[];
    secondary: string[];
    hidden: string[];
  };
}

interface TableRecordViewProps {
  records: Record[];
  validationConfig: ValidationConfig | null;
  currentPage: number;
  recordsPerPage: number;
  totalRecords: number;
  onAccept: (id: number) => void;
  onReject: (id: number) => void;
  onSetPending: (id: number) => void;
  onViewDetails: (record: Record) => void;
  onPageChange: (page: number) => void;
  onRecordsPerPageChange: (perPage: number) => void;
  onBulkAccept: () => void;
  onBulkReject: () => void;
}

export default function TableRecordView({
  records,
  validationConfig,
  currentPage,
  recordsPerPage,
  totalRecords,
  onAccept,
  onReject,
  onSetPending,
  onViewDetails,
  onPageChange,
  onRecordsPerPageChange,
  onBulkAccept,
  onBulkReject,
}: TableRecordViewProps) {
  // get primary fields from validation config
  const primaryFields = validationConfig?.field_order.primary || ["assistant"];

  // truncate text for display
  const truncateText = (text: any, maxLength: number = 100): string => {
    const str = typeof text === "string" ? text : JSON.stringify(text);
    return str.length > maxLength ? str.substring(0, maxLength) + "..." : str;
  };

  // get final accumulated state from record
  const getFinalState = (record: Record) => {
    return record.trace && record.trace.length > 0
      ? record.trace[record.trace.length - 1].accumulated_state || {}
      : {};
  };

  // calculate pagination
  const totalPages = Math.ceil(totalRecords / recordsPerPage);
  const startRecord = (currentPage - 1) * recordsPerPage + 1;
  const endRecord = Math.min(currentPage * recordsPerPage, totalRecords);

  return (
    <Box>
      {/* empty state */}
      {records.length === 0 ? (
        <Box
          sx={{
            textAlign: "center",
            py: 6,
            border: "1px dashed",
            borderColor: "border.default",
            borderRadius: 2,
          }}
        >
          <Text sx={{ color: "fg.muted", fontSize: 2 }}>No records to display</Text>
        </Box>
      ) : (
        <>
          {/* table */}
          <Box
            sx={{
              border: "1px solid",
              borderColor: "border.default",
              borderRadius: 2,
              overflow: "hidden",
              mb: 3,
            }}
          >
            <Box
              as="table"
              sx={{
                width: "100%",
                borderCollapse: "collapse",
                bg: "canvas.default",
              }}
            >
              <Box as="thead" sx={{ bg: "canvas.subtle" }}>
                <Box as="tr">
                  <Box
                    as="th"
                    sx={{
                      p: 2,
                      textAlign: "left",
                      fontWeight: "semibold",
                      fontSize: 1,
                      color: "fg.default",
                      borderBottom: "1px solid",
                      borderColor: "border.default",
                    }}
                  >
                    ID
                  </Box>
                  {primaryFields.map((field) => (
                    <Box
                      key={field}
                      as="th"
                      sx={{
                        p: 2,
                        textAlign: "left",
                        fontWeight: "semibold",
                        fontSize: 1,
                        color: "fg.default",
                        borderBottom: "1px solid",
                        borderColor: "border.default",
                      }}
                    >
                      {field}
                    </Box>
                  ))}
                  <Box
                    as="th"
                    sx={{
                      p: 2,
                      textAlign: "center",
                      fontWeight: "semibold",
                      fontSize: 1,
                      color: "fg.default",
                      borderBottom: "1px solid",
                      borderColor: "border.default",
                      width: "200px",
                    }}
                  >
                    Actions
                  </Box>
                </Box>
              </Box>
              <Box as="tbody">
                {records.map((record, index) => {
                  const finalState = getFinalState(record);
                  return (
                    <Box
                      key={record.id}
                      as="tr"
                      sx={{
                        bg: index % 2 === 0 ? "canvas.default" : "canvas.subtle",
                        "&:hover": {
                          bg: "accent.subtle",
                        },
                      }}
                    >
                      <Box
                        as="td"
                        sx={{
                          p: 2,
                          fontSize: 1,
                          color: "fg.default",
                          borderBottom: "1px solid",
                          borderColor: "border.muted",
                          fontFamily: "mono",
                        }}
                      >
                        #{record.id}
                      </Box>
                      {primaryFields.map((field) => (
                        <Box
                          key={field}
                          as="td"
                          sx={{
                            p: 2,
                            fontSize: 1,
                            color: "fg.default",
                            borderBottom: "1px solid",
                            borderColor: "border.muted",
                            maxWidth: "300px",
                          }}
                          title={
                            typeof finalState[field] === "string"
                              ? finalState[field]
                              : JSON.stringify(finalState[field])
                          }
                        >
                          {truncateText(finalState[field])}
                        </Box>
                      ))}
                      <Box
                        as="td"
                        sx={{
                          p: 2,
                          textAlign: "center",
                          borderBottom: "1px solid",
                          borderColor: "border.muted",
                        }}
                      >
                        <Box sx={{ display: "flex", gap: 1, justifyContent: "center" }}>
                          <Button
                            size="small"
                            variant="primary"
                            leadingVisual={CheckCircleIcon}
                            onClick={() => onAccept(record.id)}
                            aria-label="Accept"
                          />
                          <Button
                            size="small"
                            variant="danger"
                            leadingVisual={XCircleIcon}
                            onClick={() => onReject(record.id)}
                            aria-label="Reject"
                          />
                          <Button
                            size="small"
                            leadingVisual={EyeIcon}
                            onClick={() => onViewDetails(record)}
                            aria-label="View details"
                          />
                        </Box>
                      </Box>
                    </Box>
                  );
                })}
              </Box>
            </Box>
          </Box>

          {/* pagination and bulk actions */}
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mb: 3,
            }}
          >
            <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
              <Text sx={{ color: "fg.default", fontSize: 1 }}>
                Showing {startRecord}-{endRecord} of {totalRecords}
              </Text>
              <FormControl sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <FormControl.Label sx={{ fontSize: 1, mb: 0 }}>Per page:</FormControl.Label>
                <Select
                  value={recordsPerPage.toString()}
                  onChange={(e) => onRecordsPerPageChange(Number(e.target.value))}
                  sx={{ width: "80px" }}
                >
                  <Select.Option value="10">10</Select.Option>
                  <Select.Option value="25">25</Select.Option>
                  <Select.Option value="50">50</Select.Option>
                  <Select.Option value="100">100</Select.Option>
                </Select>
              </FormControl>
            </Box>

            <Box sx={{ display: "flex", gap: 2 }}>
              <Button
                size="small"
                onClick={() => onPageChange(currentPage - 1)}
                disabled={currentPage === 1}
              >
                Previous
              </Button>
              <Text sx={{ color: "fg.default", fontSize: 1, lineHeight: "32px" }}>
                Page {currentPage} of {totalPages}
              </Text>
              <Button
                size="small"
                onClick={() => onPageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
              >
                Next
              </Button>
            </Box>
          </Box>

          {/* bulk actions */}
          <Box sx={{ display: "flex", gap: 2 }}>
            <Button
              variant="primary"
              leadingVisual={CheckCircleIcon}
              onClick={onBulkAccept}
              disabled={records.length === 0}
            >
              Accept All Visible ({records.length})
            </Button>
            <Button
              variant="danger"
              leadingVisual={XCircleIcon}
              onClick={onBulkReject}
              disabled={records.length === 0}
            >
              Reject All Visible ({records.length})
            </Button>
          </Box>
        </>
      )}
    </Box>
  );
}
