import { CommonModule } from '@angular/common';
import { Component, OnInit, ViewChildren, QueryList, AfterViewInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Cliente, Persona, Instalacion, Puesto, Horario, Asignacion } from '../../models';
import { PatronAsignacion } from '../../models/asignacion.model';
import { ClienteService } from '../../services/cliente.service';
import { InstalacionService } from '../../services/instalacion.service';
import { PuestoService } from '../../services/puesto.service';
import { PersonaService } from '../../services/persona.service';
import { HorarioService } from '../../services/horario.service';
import { AsignacionService } from '../../services/asignacion.service';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatCardModule } from '@angular/material/card';
import { MatMenuModule } from '@angular/material/menu';
import { AsignacionCalendarioComponent } from '../asignacion-calendario/asignacion-calendario.component';
import { HttpClient } from '@angular/common/http';
import { saveAs } from 'file-saver';
import Swal from 'sweetalert2';
import { PatronAsignacionService } from '../../services/patron-asignacion.service';
import {  MatDialog, MatDialogModule } from '@angular/material/dialog';
import { PatronFormComponent } from '../patrones/patron-form/patron-form.component';
import { PatronSacafrancosModalComponent } from '../patrones/patron-sacafrancos-modal/patron-sacafrancos-modal.component';

@Component({
  selector: 'app-asignaciones',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatDialogModule,
    MatCardModule,
    MatMenuModule,
    AsignacionCalendarioComponent,
    
  ],
  templateUrl: './asignaciones.component.html',
  styleUrl: './asignaciones.component.css'
})
export class AsignacionesComponent implements OnInit {

  @ViewChildren(AsignacionCalendarioComponent)
  calendarios?: QueryList<AsignacionCalendarioComponent>;

  weeksForMonth: string[] = [];

  private monthStartToday(): string {
    const t = new Date();
    const y = t.getFullYear();
    const m = String(t.getMonth() + 1).padStart(2, '0');
    return `${y}-${m}-01`;
  }

  ngAfterViewInit(): void {
    setTimeout(() => {
        if (this.calendarios && this.calendarios.length) {
          this.calendarios.forEach(c => {
            try { c.weekStartChange.subscribe((ws: string) => {
              if (!ws) return;
              this.dia = ws;
              const parts = ws.split('-');
              if (parts.length === 3) {
                this.anio = Number(parts[0]);
                this.mes = Number(parts[1]);
                this.monthValue = `${this.anio}-${String(this.mes).padStart(2,'0')}`;
              }
              this.cargarAsignaciones();
            }); } catch(e){}
          });

          const ws = this.monthStartToday();
          this.monthValue = `${this.anio}-${String(this.mes).padStart(2,'0')}`;
          this.weeksForMonth = this.computeWeeksForMonth(this.mes, this.anio);
        }
    }, 0);
  }

  getHorasPuesto(puesto: any): string {
    try {
      if (!puesto || !puesto.horarios || !puesto.horarios.length) return '-';
      const entries: number[] = [];
      puesto.horarios.forEach((h: any) => {
        const horasVal = Number(h.horas) || 0;
        const turnoVal = (h.turno || '').toString();
        // usar key para no contar duplicado exacto de horas+turno
        const key = `${horasVal}-${turnoVal}`;
        if (!entries.some((v: any) => v.key === key)) {
          (entries as any).push({ key, horas: horasVal });
        }
      });
      const parts = (entries as any)
        .map((e: any) => e.horas)
        .sort((a: number, b: number) => a - b)
        .map((h: number) => String(h));
      return parts.length ? parts.join(' / ') : '-';
    } catch (e) {
      return '-';
    }
  }

  getTurnosPuesto(puesto: any): string {
    try {
      if (!puesto || !puesto.horarios || !puesto.horarios.length) return '-';
      const ordered = ['Diurno', 'Nocturno', 'Ambos'];
      const unique = new Set<string>();
      puesto.horarios.forEach((h: any) => {
        if (h.turno) unique.add(h.turno);
      });
      const sorted = ordered.filter(t => unique.has(t));
      const extras = [...unique].filter(t => !ordered.includes(t));
      const all = [...sorted, ...extras];
      return all.length ? all.join(', ') : '-';
    } catch (e) {
      return '-';
    }
  }

  getResumenPuestoDisplay(puesto: any): string {
    try {
      if (!puesto || !puesto.horarios || !puesto.horarios.length) return '-';
      const dayMap: any = {1: 'L', 2: 'M', 3: 'X', 4: 'J', 5: 'V', 6: 'S', 7: 'D'};
      const groups: Record<string, { horas: number; turno: string; dias: number[] }> = {};
      puesto.horarios.forEach((h: any) => {
        const horasVal = Number(h.horas) || 0;
        const turnoVal = h.turno || '';
        const key = `${horasVal}-${turnoVal}`;
        if (!groups[key]) groups[key] = { horas: horasVal, turno: turnoVal, dias: [] };
        if (h.dia && groups[key].dias.indexOf(h.dia) === -1) groups[key].dias.push(h.dia);
      });
      const parts = Object.values(groups)
        .map(g => {
          const diasStr = g.dias.sort((a, b) => a - b).map(d => dayMap[d] || '').join('');
          const base = g.turno ? `${g.horas} ${g.turno}`.trim() : `${g.horas}`;
          return diasStr ? `${base} (${diasStr})` : base;
        })
        .sort();
      return parts.length ? parts.join(' / ') : '-';
    } catch (e) {
      return '-';
    }
  }

  getResumenPuestoCompacto(puesto: any): string {
    try {
      if (!puesto || !puesto.horarios || !puesto.horarios.length) return '-';
      const dayMap: any = {1: 'L', 2: 'M', 3: 'X', 4: 'J', 5: 'V', 6: 'S', 7: 'D'};
      const groups: Record<string, { horas: number; turno: string; dias: number[] }> = {};
      puesto.horarios.forEach((h: any) => {
        const horasVal = Number(h.horas) || 0;
        const turnoVal = (h.turno || '').toString();
        const key = `${horasVal}-${turnoVal}`;
        if (!groups[key]) groups[key] = { horas: horasVal, turno: turnoVal, dias: [] };
        if (h.dia && groups[key].dias.indexOf(h.dia) === -1) groups[key].dias.push(h.dia);
      });

      const letter = (turno: string): string => {
        const t = turno.toLowerCase();
        if (t.startsWith('d')) return 'D';
        if (t.startsWith('n')) return 'N';
        if (t.startsWith('a')) return 'A';
        return '';
      };

      const parts = Object.values(groups)
        .map(g => {
          const diasStr = g.dias.sort((a: number, b: number) => a - b).map(d => dayMap[d] || '').join('');
          const base = `${g.horas}${letter(g.turno)}`.trim();
          return diasStr ? `${base} ${diasStr}` : base;
        })
        .sort((a, b) => {
          const numA = parseInt(a, 10);
          const numB = parseInt(b, 10);
          return (isNaN(numA) ? 0 : numA) - (isNaN(numB) ? 0 : numB);
        });

      const cant = puesto.cantidad_guardias ? `${puesto.cantidad_guardias}` : '';
      const body = parts.join(' / ');
      if (cant && body) return `${cant} ${body}`;
      if (cant) return `${cant}`;
      return body || '-';
    } catch (e) {
      return '-';
    }
  }

  getDiasPuesto(puesto: any): string {
    try {
      if (!puesto || !puesto.horarios || !puesto.horarios.length) return '-';
      const dayMap: any = {1: 'Lunes', 2: 'Martes', 3: 'Miércoles', 4: 'Jueves', 5: 'Viernes', 6: 'Sábado', 7: 'Domingo'};
      const diasNums = Array.from(new Set(puesto.horarios.map((h:any)=>h.dia))).sort((a:any,b:any)=>a-b);
      if (!diasNums.length) return '-';
      return diasNums.map((d:any)=> dayMap[d] || '').filter((x:any)=>x).join(', ');
    } catch (e) {
      return '-';
    }
  }

  onSharedDateChange(): void {
    if (!this.dia) {
      this.cargarAsignaciones();
      return;
    }
    // dia formato YYYY-MM-DD
    const parts = this.dia.split('-');
    if (parts.length === 3) {
      this.anio = Number(parts[0]);
      this.mes = Number(parts[1]);
    }
    // sincronizar calendario con la fecha seleccionada
    if (this.calendarios && this.calendarios.length) {
      this.calendarios.forEach(c => {
        c.weekStart = this.dia || '';
        try { c.loadWeek(); } catch(e){}
      });
    }
    this.cargarAsignaciones();
  }

  textoBotonAsignacion: string = 'Guardar';

  asignaciones: Asignacion[] = [];

  mes: number = new Date().getMonth() + 1;
  anio: number = new Date().getFullYear();
  dia: string | null = null; // formato YYYY-MM-DD (opcional)
  monthValue: string = '';

  clientes: Cliente[] = [];
  personas: Persona[] = [];
  horarios: Horario[] = [];
  instalaciones: Instalacion[] = [];
  puestos: Puesto[] = [];
  patrones: PatronAsignacion[] = [];

  clienteSeleccionado: number | null = null;
  instalacionSeleccionada: number | null = null;

  mostrarModal: boolean = false;
  asignacionActual: Asignacion = this.nuevaAsignacion();
  modoEdicion: boolean = false;
  crearCalendarioAutom = true; // crear calendario automáticamente por defecto

  constructor(
    private clienteService: ClienteService,
    private instalacionService: InstalacionService,
    private puestoService: PuestoService,
    private personaService: PersonaService,
    private horarioService: HorarioService,
    private asignacionService: AsignacionService,
    private http: HttpClient,
    private patronService: PatronAsignacionService,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    this.cargarCatalogos();
    
    this.monthValue = `${this.anio}-${String(this.mes).padStart(2,'0')}`;
    this.cargarAsignaciones();
    // inicializar semanas para el mes actual para que el ngFor tenga datos
    this.weeksForMonth = this.computeWeeksForMonth(this.mes, this.anio);
      console.log('weeksForMonth initialized', this.mes, this.anio, this.weeksForMonth);
  }

  onMonthChange(): void {
    if (!this.monthValue) return;
    const parts = this.monthValue.split('-');
    if (parts.length !== 2) return;
    this.anio = Number(parts[0]);
    this.mes = Number(parts[1]);
    this.dia = null;
    this.cargarAsignaciones();
    // sincronizar lista de semanas para el mes elegido
    this.weeksForMonth = this.computeWeeksForMonth(this.mes, this.anio);
  }

  private formatDateLocal(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  private computeWeeksForMonth(mes: number, anio: number): string[] {
    const weeksLocal: string[] = [];
    const d = new Date(anio, mes - 1, 1);
    while (d.getMonth() === (mes - 1)) {
      weeksLocal.push(this.formatDateLocal(d));
      d.setDate(d.getDate() + 7);
    }
    return weeksLocal;
  }

  cargarCatalogos(): void {
    this.clienteService.getClientes().subscribe({
      next: data => this.clientes = data,
      error: err => console.error('Error al cargar clientes', err)
    });

    this.personaService.getPersonas().subscribe({
      next: data => this.personas = data,
      error: err => console.error('Error al cargar personas', err)
    });

    this.horarioService.obtenerHorarios().subscribe({
      next: data => this.horarios = data,
      error: err => console.error('Error al cargar horarios', err)
    });
    
    this.patronService.obtenerPatrones().subscribe({
      next: data => this.patrones = data || [],
      error: err => console.error('Error al cargar patrones', err)
    });
  }

  cargarAsignaciones(): void {
    this.asignacionService.obtenerAsignaciones(this.mes, this.anio).subscribe({
      next: data => {
        this.asignaciones = data || [];
      },
      error: err => console.error('Error al cargar asignaciones', err)
    });
  }

  

  // Methods invoked by template controls to sync both calendario and asignaciones
  prevWeekAndPage(): void {
    if (this.calendarios) this.calendarios.forEach(c => { try { c.prevWeek(); } catch(e){} });
  }

  nextWeekAndPage(): void {
    if (this.calendarios) this.calendarios.forEach(c => { try { c.nextWeek(); } catch(e){} });
  }

  abrirNuevoPatron(): void {
  const ref = this.dialog.open(PatronFormComponent, { width: '480px', data: null });
  ref.afterClosed().subscribe((saved: boolean) => {
    if (saved) {
      
      this.patronService.obtenerPatrones().subscribe({ next: d => this.patrones = d || [] });
    }
  });
}

  nuevaAsignacion(): Asignacion {
    return {
      persona: 0,
      cliente: 0,
      instalacion: 0,
      puesto: 0,
      horario: 0,
      mes: this.mes,
      anio: this.anio,
      estado: 'ACTIVO',
      clienteCodigo: '',
      recurring: true
      ,patronAsignacion: 0
    };
  }

  
  onClientChange(): void {
    this.asignacionActual.cliente = this.clienteSeleccionado!;
    this.instalacionSeleccionada = null;
    this.asignacionActual.instalacion = 0;
    this.asignacionActual.puesto = 0;
    this.instalaciones = [];
    this.puestos = [];
    if (this.clienteSeleccionado) {
      this.cargarInstalaciones(this.clienteSeleccionado);
    }
  }

  onInstalacionChange(): void {
    this.asignacionActual.instalacion = this.instalacionSeleccionada!;
    this.asignacionActual.puesto = 0;
    this.puestos = [];
    if (this.instalacionSeleccionada) {
      this.cargarPuestos(this.instalacionSeleccionada);
    }
  }

  private cargarInstalaciones(clienteId: number, preselectInstalacionId?: number, preselectPuestoId?: number): void {
    this.instalacionService.getInstalaciones().subscribe({
      next: data => {
        this.instalaciones = data.filter(i => i.cliente_id === clienteId);
        if (preselectInstalacionId) {
          this.instalacionSeleccionada = preselectInstalacionId;
          this.asignacionActual.instalacion = preselectInstalacionId;
          this.cargarPuestos(preselectInstalacionId, preselectPuestoId);
        }
      },
      error: err => console.error('Error al cargar instalaciones', err)
    });
  }

  private cargarPuestos(instalacionId: number, preselectPuestoId?: number): void {
    this.puestoService.getPuestosPorInstalacion(instalacionId).subscribe({
      next: data => {
        this.puestos = data;
        if (preselectPuestoId) {
          this.asignacionActual.puesto = preselectPuestoId;
        }
      },
      error: err => console.error('Error al cargar puestos', err)
    });
  }


  abrirModalNuevo(): void {
    this.modoEdicion = false;
    this.textoBotonAsignacion = 'Guardar';
    this.asignacionActual = this.nuevaAsignacion();
    this.clienteSeleccionado = null;
    this.instalacionSeleccionada = null;
    this.instalaciones = [];
    this.puestos = [];
    if (this.clientes.length === 0 || this.personas.length === 0 || this.horarios.length === 0) {
      this.cargarCatalogos();
    }
   
    if (this.instalacionSeleccionada) {
      this.onInstalacionChange();
    }
    this.mostrarModal = true;
  }

  openSacafrancosModal(weekStart: string, day: string, puestoId?: number, manage: boolean = false){
    this.patronService.getSacafrancos(weekStart, day, puestoId).subscribe(list => {
      this.dialog.open(PatronSacafrancosModalComponent, {
        data: { lista: list, weekStart, day, puestoId, manage },
        width: '480px',
        maxHeight: '70vh',
        panelClass: 'sacafrancos-dialog'
      });
    });
  }

  descargarReporteExcel() {
  const mm = String(this.mes).padStart(2, '0');
  const url = `http://localhost:8000/api/reporte-asignaciones/?mes=${mm}&anio=${this.anio}`;
  this.http.get(url, { responseType: 'blob' })
    .subscribe({
      next: (blob) => {
        saveAs(blob, `reporte_asignaciones_${this.anio}_${mm}.xlsx`);
      },
      error: err => {
        console.error('Error descargando reporte:', err);
        Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo descargar el reporte' });
      }
    });
  }

  abrirModalEditar(asignacion: Asignacion): void {
    this.modoEdicion = true;
    this.textoBotonAsignacion = 'Actualizar';
    this.asignacionActual = { ...asignacion };

    this.clienteSeleccionado = asignacion.cliente;
    this.instalacionSeleccionada = asignacion.instalacion;

    // cargar catálogos y preseleccionar instalación y puesto del registro
    if (this.clienteSeleccionado) {
      this.cargarInstalaciones(this.clienteSeleccionado, asignacion.instalacion, asignacion.puesto);
    }

    // asegurar horarios/personas disponibles
    if (this.personas.length === 0 || this.horarios.length === 0) {
      this.cargarCatalogos();
    }

    this.mostrarModal = true;
  }

  cerrarModal(): void {
    this.mostrarModal = false;
    this.asignacionActual = this.nuevaAsignacion();
    this.clienteSeleccionado = null;
    this.instalacionSeleccionada = null;
    this.instalaciones = [];
    this.puestos = [];
  }

  guardarAsignacion(): void {

    if (!this.clienteSeleccionado) {
      Swal.fire({ icon: 'warning', title: 'Falta Cliente', text: 'Debe seleccionar un Cliente' });
      return;
    }
    if (!this.instalacionSeleccionada) {
      Swal.fire({ icon: 'warning', title: 'Falta Instalación', text: 'Debe seleccionar una Instalación' });
      return;
    }
    if (!this.asignacionActual.puesto) {
      Swal.fire({ icon: 'warning', title: 'Falta Puesto', text: 'Debe seleccionar un Puesto' });
      return;
    }
    if (!this.asignacionActual.persona) {
      Swal.fire({ icon: 'warning', title: 'Falta Persona', text: 'Debe seleccionar una Persona' });
      return;
    }
    if (!this.asignacionActual.horario) {
      Swal.fire({ icon: 'warning', title: 'Falta Horario', text: 'Debe seleccionar un Horario' });
      return;
    }

    this.asignacionActual.cliente = this.clienteSeleccionado;
    this.asignacionActual.instalacion = this.instalacionSeleccionada;
    this.asignacionActual.mes = this.mes;
    this.asignacionActual.anio = this.anio;

    const yaExiste = this.asignaciones.some(a =>
      a.persona === this.asignacionActual.persona &&
      a.mes === this.mes &&
      a.anio === this.anio &&
      (!this.modoEdicion || a.id !== this.asignacionActual.id)
    );

    if (yaExiste) {
      Swal.fire({ icon: 'warning', title: 'Duplicado', text: 'Ya existe una asignación para esta persona en este mes.' });
      return;
    }

    // No enviar fecha exacta: las asignaciones se guardan por mes y año
    // (this.asignacionActual as any).fecha = this.dia ? this.dia : null;

    if (this.modoEdicion && this.asignacionActual.id) {
      const payload = { 
        ...this.asignacionActual,
        patronAsignacion: this.asignacionActual.patronAsignacion || null
      } as any;
      this.asignacionService.actualizarAsignacion(
        this.asignacionActual.id,
        payload
      ).subscribe({
        next: () => {
          Swal.fire({ icon: 'success', title: 'Asignación actualizada', timer: 1200, showConfirmButton: false });
          this.cargarAsignaciones();
          this.cerrarModal();
          if (this.calendarios) this.calendarios.forEach(c => c.loadWeek());
        },
        error: err => {
          console.error(err);
          Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo actualizar la asignación' });
        }
      });
    } else {
      // Forzar creación de calendario semanal al crear la asignación
      const payload = { ...this.asignacionActual, patronAsignacion: this.asignacionActual.patronAsignacion || null, create_calendar: true } as any;
      this.asignacionService.crearAsignacion(payload).subscribe({
        next: () => {
          Swal.fire({ icon: 'success', title: 'Asignación creada', timer: 1200, showConfirmButton: false });
          this.cargarAsignaciones();
          this.cerrarModal();
          if (this.calendarios) this.calendarios.forEach(c => c.loadWeek());
        },
        error: err => {
          console.error(err);
          Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo crear la asignación' });
        }
      });
    }
  }

  private buildRowForPuesto(puestoId: number) {
    const puesto = this.puestos.find(p => p.id === puestoId) as any;
    const weekdayKeys = ['mon','tue','wed','thu','fri','sat','sun'];

    const normalize = (tok: any) => {
      if (!tok && tok !== 0) return '';
      const t = String(tok).trim().toLowerCase();
      const map: any = {
        l: 'lunes', lu: 'lunes', lun: 'lunes', lunes: 'lunes',
        m: 'martes', ma: 'martes', mar: 'martes', martes: 'martes',
        mi: 'miercoles', mie: 'miercoles', miercoles: 'miercoles', 'miércoles':'miercoles',
        j: 'jueves', ju: 'jueves', jue: 'jueves', jueves: 'jueves',
        v: 'viernes', vi: 'viernes', vie: 'viernes', viernes: 'viernes',
        s: 'sabado', sa: 'sabado', sab: 'sabado', sabado: 'sabado', 'sábado':'sabado',
        d: 'domingo', do: 'domingo', dom: 'domingo', domingo: 'domingo'
      };
      return map[t] || t;
    };

    const dayNames = [null,'lunes','martes','miercoles','jueves','viernes','sabado','domingo'];
    const diasNums = (puesto && puesto.horarios) ? Array.from(new Set(puesto.horarios.map((h:any)=>h.dia))) as number[] : [];
    const dias = diasNums.map((n:number)=> dayNames[n]).filter(x=>x);
    const diasNorm = dias.map(normalize).filter((x:any)=>x);
    const turnoRaw = (puesto && puesto.turno) ? String(puesto.turno).trim().toLowerCase() : (puesto && puesto.turno_display ? String(puesto.turno_display).trim().toLowerCase() : '');
    const defaultCode = turnoRaw.startsWith('n') ? 'N' : 'D';

    // Para nueva asignación queremos celdas vacías (el usuario las asigna manualmente)
    const row: any = { puesto: puestoId, puesto_detalle: puesto, mon:'',tue:'',wed:'',thu:'',fri:'',sat:'',sun:'' };
    return row;
  }

  eliminarAsignacion(asignacion: Asignacion): void {
    Swal.fire({
      title: '¿Eliminar asignación?',
      text: `${asignacion.persona_detalle?.apellidos} ${asignacion.persona_detalle?.nombres} (${asignacion.persona_detalle?.tipo})`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar'
    }).then(res => {
      if (!res.isConfirmed || !asignacion.id) return;

      this.asignacionService.eliminarAsignacion(asignacion.id).subscribe({
        next: () => {
          Swal.fire({ icon: 'success', title: 'Asignación eliminada', timer: 1200, showConfirmButton: false });
          this.cargarAsignaciones();
          if (this.calendarios) this.calendarios.forEach(c => c.loadWeek());
        },
        error: err => {
          console.error(err);
          Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudo eliminar la asignación' });
        }
      });
    });
  }

  cambiarMesAnio(): void {
    this.cargarAsignaciones();
  }
}
