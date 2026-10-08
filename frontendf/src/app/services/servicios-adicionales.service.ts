import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

// Un Servicio Adicional (formato FR-REPORTE DE PUESTO ADICIONAL).
export interface ServicioAdicional {
  id?: number;
  fecha: string;            // YYYY-MM-DD
  turno: 'Diurno' | 'Nocturno';
  cliente_id: number | null;
  cliente?: string;
  instalacion_id: number | null;
  instalacion?: string;
  cliente_texto?: string;   // columna CLIENTE: la instalación (o el cliente)
  cantidad: number;         // C: cantidad de guardias
  horas: number;            // H
  hora_ingreso: string;     // HH:MM
  hora_salida: string;
  horario?: string;         // "HH:MM - HH:MM"
  solicitado_por: string;
  recibido_por: string;
  medio: string;
  precio: number | null;    // solo con el permiso del precio
  asignacion_id?: number | null;
  sacafranco_fila_id?: number | null;
  creado_por?: string;
  modificado_por?: string;
  modificado_en?: string | null;
}

export interface CatalogoServiciosAdicionales {
  clientes: Array<{ id: number; nombre: string }>;
  instalaciones: Array<{ id: number; nombre: string; cliente_id: number; codigo: string }>;
  puede_precio: boolean;
}

@Injectable({
  providedIn: 'root',
})
export class ServiciosAdicionalesService {
  constructor(private api: ApiService) {}

  // Servicios adicionales entre dos fechas (YYYY-MM-DD), ambas incluidas.
  listar(desde: string, hasta: string): Observable<ServicioAdicional[]> {
    return this.api.get<ServicioAdicional[]>('/servicios-adicionales/', { desde, hasta });
  }

  catalogo(): Observable<CatalogoServiciosAdicionales> {
    return this.api.get<CatalogoServiciosAdicionales>('/servicios-adicionales/catalogo/');
  }

  // Desde la asistencia: el registro que ya existe para esa fila/fecha/turno, o los datos por defecto.
  prellenar(params: { fecha: string; turno: string; asignacion_id?: number | null; sacafranco_fila_id?: number | null })
    : Observable<{ existe: boolean; registro: Partial<ServicioAdicional> }> {
    const p: any = { fecha: params.fecha, turno: params.turno };
    if (params.asignacion_id) { p.asignacion_id = params.asignacion_id; }
    if (params.sacafranco_fila_id) { p.sacafranco_fila_id = params.sacafranco_fila_id; }
    return this.api.get('/servicios-adicionales/prellenar/', p);
  }

  crear(data: Partial<ServicioAdicional>): Observable<ServicioAdicional> {
    return this.api.post<ServicioAdicional>('/servicios-adicionales/crear/', data);
  }

  actualizar(id: number, data: Partial<ServicioAdicional>): Observable<ServicioAdicional> {
    return this.api.put<ServicioAdicional>(`/servicios-adicionales/${id}/`, data);
  }

  // Excel en formato FR (una pestaña por día, Diurno y Nocturno). params: desde/hasta, q.
  exportarExcel(params: any): Observable<Blob> {
    return this.api.getBlob('/servicios-adicionales/exportar-excel/', params);
  }

  // PDF en formato FR (una página por día, Diurno y Nocturno). params: desde/hasta, q.
  exportarPdf(params: any): Observable<Blob> {
    return this.api.getBlob('/servicios-adicionales/exportar-pdf/', params);
  }
}
