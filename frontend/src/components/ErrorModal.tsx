import { Dialog, Button, Flash, Text } from "@primer/react";
import { XIcon } from "@primer/octicons-react";

interface ErrorModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  message: string;
}

export default function ErrorModal({ isOpen, onClose, title, message }: ErrorModalProps) {
  return (
    <Dialog isOpen={isOpen} onDismiss={onClose} aria-labelledby="error-dialog-title">
      <Dialog.Header id="error-dialog-title">
        <Text sx={{ fontWeight: "bold", color: "danger.fg" }}>{title}</Text>
      </Dialog.Header>
      <Flash variant="danger" sx={{ m: 3 }}>
        {message}
      </Flash>
      <Dialog.Footer>
        <Button onClick={onClose} variant="primary">
          Close
        </Button>
      </Dialog.Footer>
    </Dialog>
  );
}
