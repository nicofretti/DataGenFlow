import { Meta, StoryObj } from "@storybook/react-vite";
import { Toaster } from "./sonner";
import { toast } from "sonner";
import { Button } from "./button";

const meta: Meta<typeof Toaster> = {
  title: "UI/Toaster",
  component: Toaster,
  parameters: {
    layout: "centered",
  },
};

export default meta;

type Story = StoryObj<typeof Toaster>;

export const Default: Story = {
  render: (args) => (
    <>
      <Toaster {...args} />
      <Button onClick={() => toast("This is a default toast!")} style={{ margin: 8 }}>
        Show Toast
      </Button>
    </>
  ),
};

export const Success: Story = {
  render: (args) => (
    <>
      <Toaster {...args} />
      <Button onClick={() => toast.success("Success toast!")} style={{ margin: 8 }}>
        Show Success Toast
      </Button>
    </>
  ),
};

export const Error: Story = {
  render: (args) => (
    <>
      <Toaster {...args} />
      <Button onClick={() => toast.error("Error toast!")} style={{ margin: 8 }}>
        Show Error Toast
      </Button>
    </>
  ),
};

export const Info: Story = {
  render: (args) => (
    <>
      <Toaster {...args} />
      <Button onClick={() => toast.info("Info toast!")} style={{ margin: 8 }}>
        Show Info Toast
      </Button>
    </>
  ),
};

export const Warning: Story = {
  render: (args) => (
    <>
      <Toaster {...args} />
      <Button onClick={() => toast.warning("Warning toast!")} style={{ margin: 8 }}>
        Show Warning Toast
      </Button>
    </>
  ),
};

export const Loading: Story = {
  render: (args) => (
    <>
      <Toaster {...args} />
      <Button onClick={() => toast.loading("Loading toast...")} style={{ margin: 8 }}>
        Show Loading Toast
      </Button>
    </>
  ),
};
