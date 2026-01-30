export interface AsignacionSemanal {
    id?: number;
    puesto: number;
    week_start: string; // YYYY-MM-DD (lunes)
    mon?: string;
    tue?: string;
    wed?: string;
    thu?: string;
    fri?: string;
    sat?: string;
    sun?: string;
}

// Mantengo el nombre de archivo para compatibilidad con imports existentes.
