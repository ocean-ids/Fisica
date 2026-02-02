import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { PROVINCIAS, Province, City } from '../data/provincias';

@Injectable({ providedIn: 'root' })
export class ProvinciasService {
  constructor() {}

  getProvincias(): Observable<Province[]> {
    return of(PROVINCIAS);
  }

  getCiudadesPorProvincia(provinciaId: string): Observable<City[]> {
    const p = PROVINCIAS.find(x => x.id === provinciaId);
    return of(p ? p.ciudades : []);
  }
}
