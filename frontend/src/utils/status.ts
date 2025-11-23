// get status color variant for labels
export function getStatusColor(
  status: string
): "default" | "success" | "danger" | "accent" | "attention" {
  if (status === "completed") return "success";
  if (status === "failed" || status === "cancelled") return "danger";
  if (status === "stopped") return "attention";
  return "accent";
}

// get status variant for record labels
export function getStatusVariant(
  status: string
): "default" | "success" | "danger" | "accent" | "attention" {
  switch (status) {
    case "pending":
      return "attention";
    case "accepted":
      return "success";
    case "rejected":
      return "danger";
    case "edited":
      return "accent";
    default:
      return "default";
  }
}
