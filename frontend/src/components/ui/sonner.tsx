import {
  CircleCheckIcon,
  InfoIcon,
  Loader2Icon,
  OctagonXIcon,
  TriangleAlertIcon,
} from "lucide-react";
import { useTheme } from "next-themes";
import { Toaster as Sonner, type ToasterProps } from "sonner";

const Toaster = ({ ...props }: ToasterProps) => {
  const { resolvedTheme } = useTheme();

  return (
    <Sonner
      theme={(resolvedTheme as ToasterProps["theme"]) || "dark"}
      className="toaster group"
      icons={{
        success: <CircleCheckIcon className="size-4" />,
        info: <InfoIcon className="size-4" />,
        warning: <TriangleAlertIcon className="size-4" />,
        error: <OctagonXIcon className="size-4" />,
        loading: <Loader2Icon className="size-4 animate-spin" />,
      }}
      toastOptions={{
        unstyled: true,
        classNames: {
          default: "bg-popover text-popover-foreground border-border",
          error:
            "bg-red-50 text-red-800 border-red-200 dark:bg-red-900/90 dark:text-red-50 dark:border-red-800",
          success:
            "bg-green-50 text-green-800 border-green-200 dark:bg-green-900/90 dark:text-green-50 dark:border-green-800",
          warning:
            "bg-yellow-50 text-yellow-800 border-yellow-200 dark:bg-yellow-900/90 dark:text-yellow-50 dark:border-yellow-800",
          info: "bg-blue-50 text-blue-800 border-blue-200 dark:bg-blue-900/90 dark:text-blue-50 dark:border-blue-800",
          toast:
            "p-4 border rounded-sm flex row gap-2 items-center min-w-[20rem] max-w-sm shadow-md text-sm z-100",
        },
        ...props.toastOptions,
      }}
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
          "--border-radius": "var(--radius)",
        } as React.CSSProperties
      }
      {...props}
    />
  );
};

export { Toaster };
