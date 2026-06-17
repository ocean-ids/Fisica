import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { NovedadPuesto } from '../models/novedad-puesto.model';

@Injectable({
  providedIn: 'root'
})
export class NovedadPuestoService {
  constructor(private apiService: ApiService) {}

  getNovedades(params?: { fecha?: string; cliente_id?: number; desde?: string; hasta?: string }): Observable<NovedadPuesto[]> {
    return this.apiService.get<NovedadPuesto[]>('/novedades-puesto/', params);
  }

  crearNovedad(novedad: NovedadPuesto): Observable<NovedadPuesto> {
    return this.apiService.post<NovedadPuesto>('/novedades-puesto/crear/', novedad);
  }

  actualizarNovedad(id: number, novedad: Partial<NovedadPuesto>): Observable<NovedadPuesto> {
    return this.apiService.put<NovedadPuesto>(`/novedades-puesto/${id}/`, novedad);
  }

  eliminarNovedad(id: number): Observable<any> {
    return this.apiService.delete(`/novedades-puesto/${id}/eliminar/`);
  }

  descargarExcel(fecha: string): Observable<Blob> {
    return this.apiService.getBlob('/novedades-puesto/exportar-excel/', { fecha });
  }
}
