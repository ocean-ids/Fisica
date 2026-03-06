import { Injectable } from '@angular/core';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root'
})
export class ReporteAsistenciaService {

  constructor(private apiService: ApiService){}

  getReporteAsistencia(params?: any) {
  return this.apiService.get<any[]>('/reporte-asistencia/', params);
  }

  updateReporteAsistencia(asignacionId: number, payload: any) {
    return this.apiService.put<any>(`/reporte-asistencia/${asignacionId}/`, payload);
  }
}
