import { CommonModule } from '@angular/common';
import { Component, OnInit, ViewChild, AfterViewInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Cliente, Persona, Instalacion, Puesto, Horario, Asignacion } from '../../models';
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

@Component({
  selector: 'app-asignaciones',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatCardModule
    ,MatMenuModule
    ,AsignacionCalendarioComponent
  ],
  templateUrl: './asignaciones.component.html',
  styleUrl: './asignaciones.component.css'
})
export class AsignacionesComponent implements OnInit {

  @ViewChild(AsignacionCalendarioComponent)
  calendario?: AsignacionCalendarioComponent;

  ngAfterViewInit(): void {
    // Suscribirse a cambios de semana del calendario para sincronizar filtros
    setTimeout(() => {
      if (this.calendario && this.calendario.weekStartChange) {
        this.calendario.weekStartChange.subscribe((ws: string) => {
          if (!ws) return;
          // ws es YYYY-MM-DD (lunes). Usarlo como día filtro en asignaciones
          this.dia = ws;
          const parts = ws.split('-');
          if (parts.length === 3) {
            this.anio = Number(parts[0]);
            this.mes = Number(parts[1]);
            this.monthValue = `${this.anio}-${String(this.mes).padStart(2,'0')}`;
          }
          this.cargarAsignaciones();
        });
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
    if (this.calendario) {
      this.calendario.weekStart = this.dia;
      this.calendario.loadWeek();
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
    private http: HttpClient
  ) {}

  ngOnInit(): void {
    this.cargarCatalogos();
    // inicializar selector mensual y cargar asignaciones
    this.monthValue = `${this.anio}-${String(this.mes).padStart(2,'0')}`;
    this.cargarAsignaciones();
  }

  onMonthChange(): void {
    if (!this.monthValue) return;
    const parts = this.monthValue.split('-');
    if (parts.length !== 2) return;
    this.anio = Number(parts[0]);
    this.mes = Number(parts[1]);
    this.dia = null;
    this.cargarAsignaciones();

    // calcular el primer lunes del mes y sincronizar calendario
    const firstMonday = this.getFirstMonday(this.anio, this.mes);
    if (this.calendario) {
      // Load the list of weeks for the selected month so prev/next week navigation works
      this.calendario.loadWeeksForMonth(this.mes, this.anio);
    }
  }

  private getFirstMonday(year: number, month: number): string {
    const d = new Date(year, month - 1, 1);
    const day = d.getDay(); // 0..6 Sun..Sat
    const offset = (8 - day) % 7; // days to add to reach Monday
    const dayOfMonth = 1 + offset;
    const mm = String(month).padStart(2, '0');
    const dd = String(dayOfMonth).padStart(2, '0');
    return `${year}-${mm}-${dd}`;
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
    if (this.calendario) this.calendario.prevWeek();
  }

  nextWeekAndPage(): void {
    if (this.calendario) this.calendario.nextWeek();
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
        alert('Error al descargar el reporte. Revisa la consola.');
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
      alert('Debe seleccionar un Cliente');
      return;
    }
    if (!this.instalacionSeleccionada) {
      alert('Debe seleccionar una Instalación');
      return;
    }
    if (!this.asignacionActual.puesto) {
      alert('Debe seleccionar un Puesto');
      return;
    }
    if (!this.asignacionActual.persona) {
      alert('Debe seleccionar una Persona');
      return;
    }
    if (!this.asignacionActual.horario) {
      alert('Debe seleccionar un Horario');
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
      alert('Ya existe una asignación para esta persona en este mes.');
      return;
    }

    // No enviar fecha exacta: las asignaciones se guardan por mes y año
    // (this.asignacionActual as any).fecha = this.dia ? this.dia : null;

    if (this.modoEdicion && this.asignacionActual.id) {
      this.asignacionService.actualizarAsignacion(
        this.asignacionActual.id,
        this.asignacionActual
      ).subscribe({
        next: () => {
          alert('Asignación actualizada');
          this.cargarAsignaciones();
          this.cerrarModal();
          this.calendario?.loadWeek();
        },
        error: err => {
          console.error(err);
          alert('Error al actualizar');
        }
      });
    } else {
      // Enviar create_calendar según la casilla del modal
      const payload = { ...this.asignacionActual, create_calendar: !!this.crearCalendarioAutom } as any;
      this.asignacionService.crearAsignacion(payload).subscribe({
        next: () => {
          alert('Asignación creada');
          this.cargarAsignaciones();
          this.cerrarModal();
          this.calendario?.loadWeek();
        },
        error: err => {
          console.error(err);
          alert('Error al crear');
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
    if (confirm(`¿Eliminar la asignación de ${asignacion.persona_detalle?.apellidos} ${asignacion.persona_detalle?.nombres} (${asignacion.persona_detalle?.tipo})?`)) {
      this.asignacionService.eliminarAsignacion(asignacion.id!).subscribe({
        next: () => {
          alert('Asignación eliminada');
          this.cargarAsignaciones();
          this.calendario?.loadWeek();
        },
        error: err => {
          console.error(err);
          alert('Error al eliminar');
        }
      });
    }
  }

  cambiarMesAnio(): void {
    this.cargarAsignaciones();
  }
}
