import { Component, OnInit, Output, EventEmitter, Input, OnChanges, SimpleChanges } from '@angular/core';
import { Observable, forkJoin, of } from 'rxjs';
import { AsignacionSemanal, SacafrancoFilaSemanal } from '../../models/asignacion-calendario';
import { SacafrancoFila } from '../../models/asignacion.model';
import { AsignacionCalendarioService } from '../../services/asignacion-calendario.service';
import { PuestoService } from '../../services/puesto.service';
import { AsignacionService } from '../../services/asignacion.service';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { PatronAsignacionService } from '../../services/patron-asignacion.service';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { AsignacionCalendarioRangeModalComponent, AsignacionRangeModalResult } from './asignacion-calendario-range-modal.component';


@Component({
  selector: 'app-asignacion-calendario',
  standalone: true,
  imports: [FormsModule, CommonModule, MatDialogModule, MatButtonModule],
  templateUrl: './asignacion-calendario.component.html',
  styleUrl: './asignacion-calendario.component.css'
})
export class AsignacionCalendarioComponent implements OnInit, OnChanges{
  @Input() weekStart: string = '';
  @Input() filterText: string = '';
  @Input() rowOrder: Array<number | string> = [];
  @Input() sacafrancoRows: SacafrancoFila[] = [];
  @Output() sacafrancoClick: EventEmitter<any> = new EventEmitter<any>();
  @Output() rangeApplied: EventEmitter<void> = new EventEmitter<void>();
    ngOnChanges(changes: SimpleChanges): void {
      if (changes['weekStart'] && !changes['weekStart'].firstChange) {
        this.loadWeek();
      }
      if (changes['filterText'] && !changes['filterText'].firstChange) {
        this.loadWeek();
      }
      if (changes['rowOrder'] && !changes['rowOrder'].firstChange) {
        this.applyOrder();
      }
      if (changes['sacafrancoRows'] && !changes['sacafrancoRows'].firstChange) {
        this.buildDisplayRows();
      }
    }
  weeks: string[] = [];
  currentWeekIndex: number = 0;
  weekDays: Array<{short:string, name:string, date:string, dayNum:number}> = [];
  rows: any[] = [];
  displayRows: any[] = [];
  loading = false;
  @Input() allowCreateEmptyRows: boolean = false;

  sacafrancoWeekRows: SacafrancoFilaSemanal[] = [];
  

 
  sacafrancoPreview: { [puestoId: string]: { [day: string]: string } } = {};

  constructor(
    private asignacionCalendarioService: AsignacionCalendarioService,
    private puestoService: PuestoService,
    private asignacionService: AsignacionService,
    private patronAsignacionService: PatronAsignacionService,
    private dialog: MatDialog
  ){}

  // Maneja el clic en una celda para asignar o gestionar sacafrancos, utilizando un temporizador para diferenciar entre clic simple y doble clic
  ngOnInit(): void {
    
    if (!this.weekStart) {
      this.weekStart = this.computeCurrentMonthStart();
    }

    console.log('AsignacionCalendario ngOnInit weekStart=', this.weekStart);
    this.loadWeek();
  }

  // Obtiene la fecha de inicio de la semana como un objeto Date, considerando solo la parte de la fecha
  private formatDateLocal(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  // Calcula el primer día del mes actual para usarlo como valor inicial de weekStart
  computeCurrentMonthStart(): string{
    const today = new Date();
    const y = today.getFullYear();
    const m = String(today.getMonth() + 1).padStart(2, '0');
    return `${y}-${m}-01`;
  }

  // Convierte el valor de weekStart a un objeto Date, considerando solo la parte de la fecha
  loadWeek(){
  
    this.computeWeekDays();
    this.loading = true;
    const params: any = { week_start: this.weekStart, auto_create: true };
    if (this.filterText && this.filterText.trim()) {
      params.q = this.filterText.trim();
    }
    this.asignacionCalendarioService.obtenerAsignacionesCalendario(params)
      .subscribe({
        next: (res: any) => {
        if (Array.isArray(res)) {
          this.rows = res;
        } else if (res && Array.isArray(res.results)) {
          this.rows = res.results;
        } else {
          this.rows = [];
        }

        this.applyOrder();
        this.loadSacafrancoWeek();

        
        console.log('loadWeek result for', this.weekStart, 'res=', res);
        if((!this.rows || this.rows.length === 0)){
          const parts = (this.weekStart||'').split('-').map(Number);
          const base = (parts.length===3) ? new Date(parts[0], parts[1]-1, parts[2]) : new Date();
          const mes = base.getMonth() + 1;
          const anio = base.getFullYear();
          // Si no hay filas semanales en la base, solo mostramos filas vacías por puesto
          // cuando `allowCreateEmptyRows` está habilitado. De lo contrario dejamos la tabla vacía.
          if (this.allowCreateEmptyRows) {
            this.puestoService.getPuestos().subscribe({ next: (puestos: any) => {
              const fullRows = (puestos||[]).map((p:any)=> ({ puesto: p.id, puesto_detalle: p, mon:'',tue:'',wed:'',thu:'',fri:'',sat:'',sun:'' }));
              this.rows = fullRows;
            }});
          } else {
            this.rows = [];
          }
          this.buildDisplayRows();
        }
          this.loading = false;
          
          try { this.weekStartChange.emit(this.weekStart); } catch(e){}
        },
        error: () => this.loading = false
      });
  }

  // Calcula los días de la semana basándose en el valor de weekStart para mostrar los encabezados de la tabla
  private loadSacafrancoWeek(): void {
    if (!this.weekStart) {
      this.sacafrancoWeekRows = [];
      this.buildDisplayRows();
      return;
    }
    this.asignacionCalendarioService.obtenerSacafrancoFilaSemanal({ week_start: this.weekStart })
      .subscribe({
        next: data => {
          this.sacafrancoWeekRows = data || [];
          this.buildDisplayRows();
        },
        error: () => {
          this.sacafrancoWeekRows = [];
          this.buildDisplayRows();
        }
      });
  }
  
  // Limpia la vista previa del sacafranco para un puesto y día específicos, eliminando cualquier información almacenada en el estado para esa combinación
  private getRowOrderKey(row: any): string {
    if (row?._spacer) {
      return String(row?._spacerId ?? '');
    }
    if (row?._sacafranco) {
      return `sacafranco-${row?._sacafrancoId ?? ''}`;
    }
    const key = row?.asignacion || row?.asignacion_id || row?.puesto || '';
    return String(key);
  }

  // Aplica el orden personalizado a las filas basándose en el arreglo rowOrder proporcionado
  private applyOrder(): void {
    this.buildDisplayRows();
  }

  //Construye el arreglo displayRows combinando las filas regulares y las filas de sacafranco, y aplicando el orden personalizado si se proporciona rowOrder. Las filas de sacafranco se identifican con la propiedad _sacafranco para diferenciarlas de las filas regulares.
  private buildDisplayRows(): void {
    const sacafrancoRows = this.buildSacafrancoRows();
    const combined = [...(this.rows || []), ...sacafrancoRows];
    if (!combined.length) {
      this.displayRows = [];
      return;
    }

    if (this.rowOrder && this.rowOrder.length) {
      const orderMap = new Map<string, number>();
      this.rowOrder.forEach((id, idx) => orderMap.set(String(id), idx));
      const existingKeys = new Set(combined.map(r => this.getRowOrderKey(r)));
      const placeholders = this.rowOrder
        .map(id => String(id))
        .filter(id => id.startsWith('provincia-') && !existingKeys.has(id))
        .map(id => ({ _spacer: true, _spacerId: id }));
      combined.push(...placeholders);
      combined.sort((a, b) => {
        const aKey = this.getRowOrderKey(a);
        const bKey = this.getRowOrderKey(b);
        const aIdx = orderMap.get(aKey);
        const bIdx = orderMap.get(bKey);
        const aHas = aIdx !== undefined;
        const bHas = bIdx !== undefined;
        if (aHas && bHas) return (aIdx as number) - (bIdx as number);
        if (aHas) return -1;
        if (bHas) return 1;
        return 0;
      });
    }

    this.displayRows = combined;
  }
  
  // Limpia la vista previa del sacafranco para un puesto y día específicos, eliminando cualquier información almacenada en el estado para esa combinación
  isSacafrancoHighlight(value: any): boolean {
    const raw = (value || '').toString().trim().toUpperCase();
    if (!raw) return false;
    const letter = raw.charAt(0);
    return letter === 'F' || letter === 'Q';
  }

  // Obtiene la fecha de inicio de la semana como un objeto Date, considerando solo la parte de la fecha
  private buildSacafrancoRows(): any[] {
    if (!this.sacafrancoRows || !this.sacafrancoRows.length || !this.weekStart) return [];
    const parts = this.weekStart.split('-').map(Number);
    if (parts.length !== 3) return [];
    const month = parts[1];
    const year = parts[0];
    const currentKey = (year * 12) + month;
    const weekMap = new Map<number, SacafrancoFilaSemanal>();
    (this.sacafrancoWeekRows || []).forEach(r => {
      if (r?.sacafranco_fila) weekMap.set(r.sacafranco_fila, r);
    });
    return (this.sacafrancoRows || [])
      .filter(r => {
        const rowMonth = Number(r.mes) || 0;
        const rowYear = Number(r.anio) || 0;
        const rowKey = (rowYear * 12) + rowMonth;
        return rowKey > 0 && rowKey <= currentKey;
      })
      .sort((a, b) => (a.orden ?? 0) - (b.orden ?? 0))
      .map(r => {
        const week = weekMap.get(r.id as number);
        return {
          _sacafranco: true,
          _sacafrancoId: r.id,
          mon: week?.mon || '',
          tue: week?.tue || '',
          wed: week?.wed || '',
          thu: week?.thu || '',
          fri: week?.fri || '',
          sat: week?.sat || '',
          sun: week?.sun || ''
        };
      });
  }

  // Obtiene la fecha correspondiente a un día de la semana específico basándose en la fecha de inicio de la semana (weekStart) y la clave del día (dayKey), considerando solo la parte de la fecha
  loadWeeksForMonth(mes: number, anio: number){
    const weeksLocal: string[] = [];
    const d = new Date(anio, mes - 1, 1);
    while (d.getMonth() === (mes - 1)) {
      weeksLocal.push(this.formatDateLocal(d));
      d.setDate(d.getDate() + 7);
    }

    this.weeks = weeksLocal;
    const idx = this.weeks.indexOf(this.weekStart);
    this.currentWeekIndex = idx >= 0 ? idx : 0;
    if (this.weeks.length){
      this.weekStart = this.weeks[this.currentWeekIndex] || this.weeks[0];
    } else {
      this.weekStart = '';
    }
    this.loadWeek();
  }

  // Calcula la fecha de la semana anterior basándose en el arreglo weeks y actualiza el estado para mostrar la nueva semana
  prevWeek(){
    if(this.currentWeekIndex > 0){
      this.currentWeekIndex -= 1;
      this.weekStart = this.weeks[this.currentWeekIndex];
      this.loadWeek();
    }
  }

  // Calcula la fecha de la siguiente semana basándose en el arreglo weeks y actualiza el estado para mostrar la nueva semana
  nextWeek(){
    if(this.currentWeekIndex < this.weeks.length - 1){
      this.currentWeekIndex += 1;
      this.weekStart = this.weeks[this.currentWeekIndex];
      this.loadWeek();
    }
  }

        @Output() weekStartChange: EventEmitter<string> = new EventEmitter<string>();
  
  saveRow(row: any){
    const asignacionId = row.asignacion || row.asignacion_id;
    if (!asignacionId) {
      // Evita crear filas semanales huerfanas sin asignacion padre.
      return;
    }

    const payload: any = {
    puesto: row.puesto || (row.puesto_detalle && row.puesto_detalle.id),
    week_start: this.weekStart,
    mon: row.mon || '',
    tue: row.tue || '',
    wed: row.wed || '',
    thu: row.thu || '',
    fri: row.fri || '',
    sat: row.sat || '',
    sun: row.sun || ''
  };
  payload.asignacion_id = asignacionId;
  this.asignacionCalendarioService.crearAsignacionCalendario(payload)
    .subscribe({
      next: () => {},
      error: () => {}
    });
  }
  
  // Guarda los cambios en una fila de sacafranco enviando solo los días que fueron modificados para optimizar la actualización
  onCellChange(row: any, day: string, value: any){
    const v = value ? String(value).toUpperCase().slice(0,4) : '';
    row[day] = v;
    this.saveRow(row);
  }

  // Maneja el evento de cambio en una celda de sacafranco, actualizando el valor en la fila y luego llamando a la función para guardar los cambios en el backend
  onSacafrancoCellChange(row: any, day: string, value: any){
    const v = value ? String(value).toUpperCase().slice(0, 5) : '';
    row[day] = v;
    this.saveSacafrancoRow(row, [day]);
  }

  // Guarda los cambios en una fila de sacafranco enviando solo los días que fueron modificados para optimizar la actualización
  private saveSacafrancoRow(row: any, days: string[]): void {
    const filaId = row?._sacafrancoId;
    if (!filaId) return;
    const payload: any = {
      sacafranco_fila: filaId,
      week_start: this.weekStart
    };
    days.forEach(d => {
      payload[d] = row[d] || '';
    });
    this.asignacionCalendarioService.crearSacafrancoFilaSemanal(payload)
      .subscribe({ next: () => {}, error: () => {} });
  }

  // Obtiene la fecha de finalización de la secuencia basándose en la fecha de inicio y la cantidad de tokens, considerando solo la parte de la fecha
  getCellClass(value: string){
    if(!value) return '';
    const v = value.toString().toUpperCase();
    if(v.startsWith('F')) return 'cell-franco';
    if(v.startsWith('D')) return 'cell-dia';
    if(v.startsWith('N')) return 'cell-noche';
    if(v.startsWith('DS') || v.startsWith('NS')) return 'cell-desc';
    if(v.startsWith('MA') || v.startsWith('MI')) return 'cell-daycode';
    return '';
  }

  dayKeyFromDate(dateStr: string): string {
   
    if(!dateStr) return '';
    try {
      const parts = dateStr.split('-').map(Number);
      if (parts.length !== 3) return '';
      const d = new Date(parts[0], parts[1]-1, parts[2]);
      const map = ['sun','mon','tue','wed','thu','fri','sat'];
      return map[d.getDay()];
    } catch (e) {
      return '';
    }
  }
  
  computeWeekDays(): void {
    this.weekDays = [];
    if (!this.weekStart) return;
    const parts = this.weekStart.split('-').map(Number);
    if (parts.length !== 3) return;
    const base = new Date(parts[0], parts[1]-1, parts[2]);
    const baseMonth = base.getMonth();
    const shortOrder = ['Do','Lu','Ma','Mi','Ju','Vi','Sá'];
    const fullOrder = ['domingo','lunes','martes','miércoles','jueves','viernes','sábado'];

    for (let i = 0; i < 7; i++){
      const d = new Date(base);
      d.setDate(base.getDate() + i);
      const dow = d.getDay();
      const inMonth = d.getMonth() === baseMonth;
      this.weekDays.push({
        short: shortOrder[dow],
        name: fullOrder[dow],
        date: inMonth ? this.formatDateLocal(d) : '',
        dayNum: inMonth ? d.getDate() : 0
      });
    }
  }

  // Maneja el clic en una celda para asignar o gestionar sacafrancos, utilizando un temporizador para diferenciar entre clic simple y doble clic
  private _clickTimer: any = null;

  handleCellClick(event: MouseEvent, row: any, day: string, puestoId: any) {
    event.stopPropagation();
   
    if (this._clickTimer) return;
    this._clickTimer = setTimeout(() => {
      this._clickTimer = null;
      this.sacafrancoClick.emit({ weekStart: this.weekStart, day: day, puestoId: puestoId, manage: false });
    }, 250);
  }

  handleCellDblClick(event: MouseEvent, row: any, day: string, puestoId: any) {
    event.stopPropagation();
    if (this._clickTimer) {
      clearTimeout(this._clickTimer);
      this._clickTimer = null;
    }
    this.sacafrancoClick.emit({ weekStart: this.weekStart, day: day, puestoId: puestoId, manage: true });
  }

  // Abre el modal de asignación por rango para un puesto y día específicos, prellenando los campos de fecha basándose en la celda clicada, y luego maneja el resultado para aplicar los cambios tanto al backend como a la vista previa de manera eficiente
  openRangeModal(row: any, dayKey: string, isSacafranco: boolean): void {
    const clickedDate = this.getDateForDayKey(this.weekStart, dayKey);
    if (!clickedDate) return;
    const startDefault = this.formatDateLocal(clickedDate);
    const endDefault = this.formatDateLocal(clickedDate);
    const ref = this.dialog.open(AsignacionCalendarioRangeModalComponent, {
      width: '420px',
      data: {
        start: startDefault,
        end: endDefault,
        seq: '',
        isSacafranco,
        weekStart: this.weekStart,
        row
      }
    });

    ref.afterClosed().subscribe((result?: AsignacionRangeModalResult) => {
      if (!result) return;
      const { start, end, seq } = result;
      if (!start || !end || !seq) return;

      const startDate = new Date(start + 'T00:00:00');
      const endDate = new Date(end + 'T00:00:00');
      if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) return;

      const tokens = this.parseSequence(seq, isSacafranco);
      if (!tokens.length) return;

      const anchor = this.parseWeekStart(this.weekStart);
      const rangeMap = this.buildRangeMap(startDate, endDate, tokens, anchor);
      this.applyRangeToBackend(row, rangeMap, isSacafranco).subscribe({
        next: () => {
          this.applyRangeToCurrentWeek(row, rangeMap);
          this.rangeApplied.emit();
        },
        error: () => {
          this.applyRangeToCurrentWeek(row, rangeMap);
          this.rangeApplied.emit();
        }
      });
    });
  }

  // Parsea la secuencia ingresada en un arreglo de tokens, diferenciando entre secuencias de sacafranco (que pueden contener códigos más complejos) y secuencias regulares (que se limitan a letras F, D, N)
  private parseSequence(seq: string, isSacafranco: boolean): string[] {
    const raw = (seq || '').trim().toUpperCase();
    if (!raw) return [];
    if (!isSacafranco) {
      const letters = raw.match(/[FDN]/g) || [];
      return letters;
    }
    const parts = raw.split(/[\s,]+/).filter(Boolean);
    return parts.length ? parts : [raw];
  }

  // Construye un mapa de rangos que asigna a cada semana y día el token correspondiente de la secuencia, basándose en las fechas de inicio y fin proporcionadas, y opcionalmente anclando la secuencia a una semana específica para mantener la consistencia visual
  private buildRangeMap(startDate: Date, endDate: Date, tokens: string[], anchorWeekStart?: Date | null): Record<string, Record<string, string>> {
    const map: Record<string, Record<string, string>> = {};
    let idx = 0;
    const d = new Date(startDate);
    const anchorStart = anchorWeekStart ? new Date(anchorWeekStart) : null;
    const anchorEnd = anchorStart ? new Date(anchorStart) : null;
    if (anchorEnd) anchorEnd.setDate(anchorEnd.getDate() + 6);
    while (d <= endDate) {
      const weekStart = (anchorStart && anchorEnd && d >= anchorStart && d <= anchorEnd)
        ? anchorStart
        : this.getWeekStartForDate(d);
      const weekKey = this.formatDateLocal(weekStart);
      const dayKey = this.dayKeyFromDate(this.formatDateLocal(d));
      if (!map[weekKey]) map[weekKey] = {};
      map[weekKey][dayKey] = tokens[idx % tokens.length];
      idx += 1;
      d.setDate(d.getDate() + 1);
    }
    return map;
  }

  // Parsea una fecha en formato string a un objeto Date, considerando solo la parte de la fecha, y devuelve null si el formato es inválido o si la fecha no es válida
  private parseWeekStart(weekStartStr: string): Date | null {
    if (!weekStartStr) return null;
    const parts = weekStartStr.split('-').map(Number);
    if (parts.length !== 3) return null;
    return new Date(parts[0], parts[1] - 1, parts[2]);
  }

  // Obtiene la fecha de inicio de la semana para una fecha dada, considerando solo la parte de la fecha
  private getWeekStartForDate(d: Date): Date {
    const y = d.getFullYear();
    const m = d.getMonth();
    const day = d.getDate();
    const startDay = 1 + Math.floor((day - 1) / 7) * 7;
    return new Date(y, m, startDay);
  }

  // obtiene la fecha correspondiente a una clave de día de la semana (mon, tue, wed, etc.) basándose en el weekStart y el día clave proporcionados
  private getDateForDayKey(weekStartStr: string, dayKey: string): Date | null {
    if (!weekStartStr || !dayKey) return null;
    const parts = weekStartStr.split('-').map(Number);
    if (parts.length !== 3) return null;
    const base = new Date(parts[0], parts[1] - 1, parts[2]);
    for (let i = 0; i < 7; i++) {
      const d = new Date(base);
      d.setDate(base.getDate() + i);
      if (this.dayKeyFromDate(this.formatDateLocal(d)) === dayKey) return d;
    }
    return null;
  }

  // Aplica los cambios de la secuencia a la base de datos enviando solo los dias que fueron modificados para optimizar la actualización, y diferenciando entre filas regulares de asignación y filas de sacafranco para usar los endpoints correspondientes
  private applyRangeToBackend(row: any, rangeMap: Record<string, Record<string, string>>, isSacafranco: boolean): Observable<any> {
    const requests: Observable<any>[] = [];
    const keys = Object.keys(rangeMap);
    keys.forEach(weekStart => {
      const days = rangeMap[weekStart] || {};
      if (!Object.keys(days).length) return;
      if (isSacafranco) {
        const filaId = row?._sacafrancoId;
        if (!filaId) return;
        const payload: any = { sacafranco_fila: filaId, week_start: weekStart };
        Object.keys(days).forEach(k => payload[k] = days[k]);
        requests.push(this.asignacionCalendarioService.crearSacafrancoFilaSemanal(payload));
      } else {
        const asignacionId = row?.asignacion || row?.asignacion_id;
        if (!asignacionId) return;
        const payload: any = {
          asignacion_id: asignacionId,
          puesto: row.puesto || (row.puesto_detalle && row.puesto_detalle.id),
          week_start: weekStart
        };
        Object.keys(days).forEach(k => payload[k] = days[k]);
        requests.push(this.asignacionCalendarioService.crearAsignacionCalendario(payload));
      }
    });
    return requests.length ? forkJoin(requests) : of(null);
  }

  // Aplica los cambios de la secuencia a la fila actual en la vista previa, actualizando solo los días que fueron modificados para reflejar inmediatamente los cambios sin necesidad de recargar toda la semana
  private applyRangeToCurrentWeek(row: any, rangeMap: Record<string, Record<string, string>>): void {
    const weekDays = rangeMap[this.weekStart] || {};
    Object.keys(weekDays).forEach(k => {
      row[k] = weekDays[k];
    });
  }

  //Muestra una vista previa del sacafranco asignado para un puesto y dia especificos obteniendo los datos desde el backend solo si no se ha cargado previamente para evitar llamadas redundantes, y maneja los estados de carga y error para mostrar la información de manera eficiente
  showPreview(puestoId: any, day: string) {
    try {
      const key = String(puestoId || '');
      this.sacafrancoPreview[key] = this.sacafrancoPreview[key] || {};  
      if (this.sacafrancoPreview[key][day]) return;

      this.patronAsignacionService.getSacafrancos(this.weekStart, day, puestoId)
        .subscribe({
          next: (list: any[]) => {
            const assigned = (list || []).find(p => p.assigned_for_puesto || p.status === 'assigned');
            if (assigned) {
              this.sacafrancoPreview[key][day] = (assigned.nombre || assigned.first_name || '') + (assigned.apellidos ? (' ' + assigned.apellidos) : '');
            } else {
              this.sacafrancoPreview[key][day] = 'Sin asignar';
            }
          },
          error: () => { this.sacafrancoPreview[key][day] = ''; }
        });
    } catch (e) {}
  }

  // Limpia la vista previa del sacafranco para un puesto y dia especificos, eliminando la información almacenada en el estado para que no se muestre más en la interfaz
  clearPreview(puestoId: any, day: string) {
    const key = String(puestoId || '');
    if (this.sacafrancoPreview[key]) this.sacafrancoPreview[key][day] = '';
  }

  // Obtiene el titulo de la vista previa del sacafranco para un puesto y dia especificos desde el estado, devolviendo una cadena vacía si no hay información disponible para mostrar
  getPreviewTitle(puestoId: any, day: string) {
    const key = String(puestoId || '');
    return (this.sacafrancoPreview[key] && this.sacafrancoPreview[key][day]) || '';
  }

  // Maneja el evento de clic en el ícono de información para un puesto y día específicos, deteniendo la propagación del evento y emitiendo un evento personalizado con la información relevante
  onInfoClick(event: MouseEvent, puestoId: any, day: string) {
    event.stopPropagation();
    
    this.sacafrancoClick.emit({ weekStart: this.weekStart, day: day, puestoId: puestoId, manage: true });
  }

}
