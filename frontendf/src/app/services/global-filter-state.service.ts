import { Injectable } from '@angular/core';
import { BehaviorSubject, Subject } from 'rxjs';
import { GlobalFilterState } from '../models/global-filter.model';

// Estado de navegación entre coincidencias (flechas dentro del buscador).
export interface MatchNavState {
  route: string;
  count: number;   // total de coincidencias
  index: number;   // coincidencia actual (0-based)
}

@Injectable({
  providedIn: 'root',
})
export class GlobalFilterStateService {
  private stateSubject = new BehaviorSubject<GlobalFilterState>({ route: '', query: '' });
  state$ = this.stateSubject.asObservable();

  // Estado de coincidencias que publica la página activa (ej. Asignaciones).
  private matchNavSubject = new BehaviorSubject<MatchNavState>({ route: '', count: 0, index: 0 });
  matchNav$ = this.matchNavSubject.asObservable();

  // Acciones (siguiente/anterior) que dispara el buscador hacia la página.
  private matchNavActionSubject = new Subject<'next' | 'prev'>();
  matchNavAction$ = this.matchNavActionSubject.asObservable();

  setQuery(query: string, route: string): void {
    this.stateSubject.next({ route, query });
  }

  setMatchNav(count: number, index: number, route: string): void {
    this.matchNavSubject.next({ route, count, index });
  }

  emitMatchNavAction(action: 'next' | 'prev'): void {
    this.matchNavActionSubject.next(action);
  }
}
