import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";

/* Helper para combinar clases */
function cn(...classes: (string | undefined | false)[]) {
    return classes.filter(Boolean).join(" ");
}

/* ROOT */
const Dialog = DialogPrimitive.Root;
const DialogTrigger = DialogPrimitive.Trigger;
const DialogPortal = DialogPrimitive.Portal;
const DialogClose = DialogPrimitive.Close;

/* OVERLAY */
const DialogOverlay = React.forwardRef<
    React.ElementRef<typeof DialogPrimitive.Overlay>,
    React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
    <DialogPrimitive.Overlay
        ref={ref}
        className={cn(
            "fixed inset-0 z-50 bg-black/70",
            className
        )}
        {...props}
    />
));
DialogOverlay.displayName = "DialogOverlay";

/* CONTENT */
const DialogContent = React.forwardRef<
    React.ElementRef<typeof DialogPrimitive.Content>,
    React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>
>(({ className, children, ...props }, ref) => (
    <DialogPortal>
        <DialogOverlay />

        <DialogPrimitive.Content
            ref={ref}
            className={cn(
                "fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2",
                "bg-white border border-border-soft rounded-2xl shadow-lg",
                "p-0",
                "animate-in fade-in zoom-in-95 duration-200",
                className
            )}
            {...props}
        >
            <div className="max-h-[85vh] overflow-y-auto p-6 space-y-4">
                {children}
            </div>

            {/* BOTÓN CERRAR */}
            <DialogPrimitive.Close
                className="absolute right-4 top-4 rounded-md opacity-70 hover:opacity-100 hover:bg-hover p-1 transition"
            >
                <X className="h-4 w-4" />
                <span className="sr-only">Cerrar</span>
            </DialogPrimitive.Close>
        </DialogPrimitive.Content>
    </DialogPortal>
));
DialogContent.displayName = "DialogContent";

/* HEADER */
const DialogHeader = ({
    className,
    ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
    <div
        className={cn("flex flex-col space-y-1 text-left", className)}
        {...props}
    />
);
DialogHeader.displayName = "DialogHeader";

/* FOOTER */
const DialogFooter = ({
    className,
    ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
    <div
        className={cn(
            "flex flex-col-reverse sm:flex-row sm:justify-end gap-2",
            className
        )}
        {...props}
    />
);
DialogFooter.displayName = "DialogFooter";

/* TITLE */
const DialogTitle = React.forwardRef<
    React.ElementRef<typeof DialogPrimitive.Title>,
    React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>
>(({ className, ...props }, ref) => (
    <DialogPrimitive.Title
        ref={ref}
        className={cn("text-lg font-semibold text-neutral-dark", className)}
        {...props}
    />
));
DialogTitle.displayName = "DialogTitle";

/* DESCRIPTION */
const DialogDescription = React.forwardRef<
    React.ElementRef<typeof DialogPrimitive.Description>,
    React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>
>(({ className, ...props }, ref) => (
    <DialogPrimitive.Description
        ref={ref}
        className={cn("text-sm text-neutral-light", className)}
        {...props}
    />
));
DialogDescription.displayName = "DialogDescription";

/* EXPORTS */
export {
    Dialog,
    DialogPortal,
    DialogOverlay,
    DialogClose,
    DialogTrigger,
    DialogContent,
    DialogHeader,
    DialogFooter,
    DialogTitle,
    DialogDescription,
};