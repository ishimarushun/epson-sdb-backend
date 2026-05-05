export type PublicPrinter = {
  id: number;
  name: string;
  location: string;
};

export type PublicConfig = {
  printing_enabled: boolean;
  landing_title: string;
  landing_body: string;
  printer_mode: "single" | "select" | "all";
  allow_image_uploads: boolean;
  max_text_length: number;
  max_image_bytes: number;
  printers: PublicPrinter[];
};

export type AdminPrinter = PublicPrinter & {
  printer_sdp_id: string;
  enabled: boolean;
  public_selectable: boolean;
  is_default: boolean;
};

export type AdminConfig = Omit<PublicConfig, "printers"> & {
  default_printer_id: number | null;
  max_image_pixels: number;
  updated_at: string;
};

export type PrintJob = {
  id: number;
  printer_id: string;
  type: string;
  text: string;
  image_base64: string | null;
  copies: number;
  status: string;
  printer_response: string | null;
  created_at: string;
  updated_at: string;
};
