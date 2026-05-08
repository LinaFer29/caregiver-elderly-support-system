import * as Icons from "lucide-react";

type Props = {
    name: string;
    size?: number;
    className?: string;
    style?: React.CSSProperties;
};

export function DynamicIcon({
    name,
    size = 20,
    className,
    style,
}: Props) {
    // Convertir String a componente de icono
    const iconName = name
    const LucideIcon = (Icons as any)[iconName];
    
    if(!LucideIcon) {
        //fallback a un icono por defecto si el nombre no es válido
        return <Icons.HelpCircle size={size} className={className} style={style} />;
    }

    return <LucideIcon size={size} className={className} style={style} />;
}
