import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Observable } from 'rxjs';
import { HttpParams } from '@angular/common/http';

@Injectable({
  providedIn: 'root'
})
export class UbicacionService {

  constructor(private apiService: ApiService) { }

  getProvincias(): Observable<any[]> {
    return this.apiService.get<any[]>('/provincias/');
  }

  getCantones(provinciaId?: number): Observable<any[]>{
    let params = new HttpParams();
    if (provinciaId) params = params.set('provincia_id', provinciaId);
    return this.apiService.get<any[]>('/cantones/', {params});
  }

  getInstalaciones(clienteId?: number, q?:string): Observable<any[]>{
    let params = new HttpParams();
    if (clienteId) params = params.set('cliente_id', clienteId);
    if (q) params = params.set('q', q);
    return this.apiService.get<any[]>('/instalaciones/', {params});
  }

  getZonas(instalacionId: number): Observable<any[]> {
    const params = new HttpParams().set('instalacion_id', instalacionId);
    return this.apiService.get<any[]>('/zonas/', {params})
  }
}
