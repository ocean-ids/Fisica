import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

// Un ADICIONAL del Reporte de Guardia (se llena desde la asistencia). Sin valores.
export interface ServicioAdicional {
  id: number;
  fecha: string;          // YYYY-MM-DD
  turno: string;          // Diurno / Nocturno
  cliente: string;
  puesto: string;
  persona_nombre: string; // 1 nombre y 2 apellidos
  proviene: string;
}

@Injectable({
  providedIn: 'root',
})
export class ServiciosAdicionalesService {
  constructor(private api: ApiService) {}

  // Adicionales entre dos fechas (YYYY-MM-DD), ambas incluidas.
  listar(desde: string, hasta: string): Observable<ServicioAdicional[]> {
    return this.api.get<ServicioAdicional[]>('/servicios-adicionales/', { desde, hasta });
  }

  // Excel (mismas columnas que la tabla). params: desde/hasta, turno, q.
  exportarExcel(params: any): Observable<Blob> {
    return this.api.getBlob('/servicios-adicionales/exportar-excel/', params);
  }
}
