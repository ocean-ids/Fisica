import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { GlobalFilterState } from '../models/global-filter.model';

@Injectable({
  providedIn: 'root',
})
export class GlobalFilterStateService {
  private stateSubject = new BehaviorSubject<GlobalFilterState>({ route: '', query: '' });
  state$ = this.stateSubject.asObservable();

  setQuery(query: string, route: string): void {
    this.stateSubject.next({ route, query });
  }
}
