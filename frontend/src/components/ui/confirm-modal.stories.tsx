import { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { ConfirmModal } from "./confirm-modal";
import { Button } from "./button";

const meta: Meta<typeof ConfirmModal> = {
  title: "UI/ConfirmModal",
  component: ConfirmModal,
  parameters: {
    layout: "centered",
  },
};

export default meta;

type Story = StoryObj<typeof ConfirmModal>;

export const Danger: Story = {
  render: () => {
    const [open, setOpen] = useState(false);
    return (
      <>
        <Button variant="destructive" onClick={() => setOpen(true)}>
          Delete Pipeline
        </Button>
        <ConfirmModal
          open={open}
          onOpenChange={setOpen}
          title="Delete Pipeline"
          description="This action cannot be undone. This will permanently delete the pipeline and all associated data."
          onConfirm={async () => {
            await new Promise((resolve) => setTimeout(resolve, 1000));
            console.log("deleted");
          }}
          variant="danger"
          confirmText="Delete"
        />
      </>
    );
  },
};

export const Warning: Story = {
  render: () => {
    const [open, setOpen] = useState(false);
    return (
      <>
        <Button onClick={() => setOpen(true)}>Reset Settings</Button>
        <ConfirmModal
          open={open}
          onOpenChange={setOpen}
          title="Reset Settings"
          description="This will reset all your preferences to default values. You can reconfigure them later."
          onConfirm={async () => {
            await new Promise((resolve) => setTimeout(resolve, 1000));
            console.log("reset");
          }}
          variant="warning"
          confirmText="Reset"
        />
      </>
    );
  },
};

export const Info: Story = {
  render: () => {
    const [open, setOpen] = useState(false);
    return (
      <>
        <Button onClick={() => setOpen(true)}>Publish Changes</Button>
        <ConfirmModal
          open={open}
          onOpenChange={setOpen}
          title="Publish Changes"
          description="Your changes will be visible to all users immediately after publishing."
          onConfirm={async () => {
            await new Promise((resolve) => setTimeout(resolve, 1000));
            console.log("published");
          }}
          variant="info"
          confirmText="Publish"
        />
      </>
    );
  },
};

export const CustomButtons: Story = {
  render: () => {
    const [open, setOpen] = useState(false);
    return (
      <>
        <Button variant="destructive" onClick={() => setOpen(true)}>
          Remove User
        </Button>
        <ConfirmModal
          open={open}
          onOpenChange={setOpen}
          title="Remove User"
          description="Are you sure you want to remove this user from the project?"
          onConfirm={async () => {
            await new Promise((resolve) => setTimeout(resolve, 1000));
            console.log("removed");
          }}
          variant="danger"
          confirmText="Yes, remove"
          cancelText="No, keep user"
        />
      </>
    );
  },
};
