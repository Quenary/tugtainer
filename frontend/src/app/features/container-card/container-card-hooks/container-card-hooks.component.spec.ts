import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideTranslateService } from '@ngx-translate/core';
import { ContainerCardHooksComponent } from './container-card-hooks.component';
import { IContainerHooks } from 'src/app/features/containers/containers.interface';

describe('ContainerCardHooksComponent', () => {
  let component: ContainerCardHooksComponent;
  let fixture: ComponentFixture<ContainerCardHooksComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerCardHooksComponent],
      providers: [provideTranslateService()],
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerCardHooksComponent);
    component = fixture.componentInstance;
  });

  it('should create with empty hooks', () => {
    fixture.componentRef.setInput('hooks', null);
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  describe('form', () => {
    it('fills fields from the hooks input', () => {
      const hooks: IContainerHooks = {
        pre_update: ['echo one', 'echo two'],
        post_update: [],
        pre_stop: [],
        pre_rollback: [],
        post_rollback: [],
      };
      fixture.componentRef.setInput('hooks', hooks);
      fixture.detectChanges();

      expect(component['form'].controls.pre_update.value).toBe(
        'echo one\necho two',
      );
    });

    it('emits lines split into an array, with blank lines stripped', () => {
      fixture.componentRef.setInput('hooks', null);
      fixture.detectChanges();

      const emitted: IContainerHooks[] = [];
      component.save.subscribe((v) => emitted.push(v));

      component['form'].controls.pre_update.setValue('echo one\n\necho two\n');
      component['onSave']();

      expect(emitted).toHaveLength(1);
      expect(emitted[0].pre_update).toEqual(['echo one', 'echo two']);
      expect(emitted[0].post_update).toEqual([]);
    });
  });
});
