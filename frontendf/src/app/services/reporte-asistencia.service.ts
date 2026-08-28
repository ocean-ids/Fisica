import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { ReporteAsistenciaHistorialItem, ReporteAsistenciaListResponse, ReporteAsistenciaRow, UpdateReporteAsistenciaPayload } from '../models';

@Injectable({
  providedIn: 'root'
})
export class ReporteAsistenciaService {

  constructor(private apiService: ApiService){}

  getReporteAsistencia(params?: any) {
    return this.apiService.get<ReporteAsistenciaListResponse>('/reporte-asistencia/', params);
  }

  updateReporteAsistencia(asignacionId: number, payload: UpdateReporteAsistenciaPayload) {
    return this.apiService.put<ReporteAsistenciaRow>(`/reporte-asistencia/${asignacionId}/`, payload);
  }

  // Marca la asistencia/edición (FALTÓ, hueca, descripción, color...) de un SACAFRANCO
  // (no tiene asignacion; se guarda por su fila).
  updateSacafrancoAsistencia(sacafrancoFilaId: number, payload: Partial<UpdateReporteAsistenciaPayload> & { fecha: string | null; estado_asistencia: string | null }) {
    return this.apiService.put<ReporteAsistenciaRow>(`/reporte-asistencia/sacafranco/${sacafrancoFilaId}/`, payload);
  }

  getReporteAsistenciaHistorial(asignacionId: number, params?: any) {
    return this.apiService.get<ReporteAsistenciaHistorialItem[]>(`/reporte-asistencia/${asignacionId}/historial/`, params);
  }

  getDescripciones(){
    return this.apiService.get<string[]>('/reporte-asistencia/descripciones/');
  }

  exportarExcel(params?: any) {
    return this.apiService.getBlob('/reporte-asistencia/exportar-excel/', params);
  }

  exportarPdf(params?: any) {
    return this.apiService.getBlob('/reporte-asistencia/exportar-pdf/', params);
  }

}
