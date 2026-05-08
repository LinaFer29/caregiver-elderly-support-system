type BaseCategory = {
    name: string;
    color: string;
    icon : string;
}

export type Category = BaseCategory & { // Data From the backend
    id: number;
  };

export type CategoryCreate = BaseCategory // Data you SEND to the backend

export const CATEGORY_ICONS = [
  "Tags","Heart", "Pill", "Utensils", "Sun", "Moon", "Droplets",
  "Footprints", "Brain", "Eye", "Ear", "Music", "BookOpen",
  "Phone", "ShoppingCart", "Car", "House", "Flower2", "Stethoscope",
];

export const CATEGORY_COLORS = [
  "#4BA3C7", "#5BB98C", "#F4A261", "#E76F6F",
  "#9B8EC4", "#E091B7", "#6BB5D9", "#7EC8A0",
  "#D4A373", "#C9ADA7", "#81B29A", "#F2CC8F",
];