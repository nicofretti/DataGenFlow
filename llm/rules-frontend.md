# Frontend Code Guide - DataGenFlow

**version**: 1.0
**focus**: keep it simple, maintainable, and performant

---

## core principles

**1. components should be focused**
```tsx
// bad: bloated component doing too much
export default function Review() {
  const [records, setRecords] = useState(...);
  // ... many useState hooks
  // ... many useEffect hooks
  // ... complex business logic mixed with UI
}

// good: extract hooks and separate concerns
export default function Review() {
  const { records } = useRecords(pipelineId);
  const { currentIndex } = useNavigation();
  return <ReviewContent records={records} currentIndex={currentIndex} />;
}
```

**2. explicit over implicit**
```tsx
// bad
function RecordView() {
  const data = useContext(SomeContext);  // hidden
  return <div>{data.name}</div>;
}

// good
function RecordView({ name }: Props) {
  return <div>{name}</div>;
}
```

**3. fail loudly, never silently**
```tsx
// bad
try {
  const data = await fetch("/api/job");
} catch {
  // user sees nothing!
}

// good
try {
  const res = await fetch("/api/job");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
} catch (err) {
  console.error("job fetch failed:", err);
  showToast({ type: "error", message: err.message });
}
```

**4. single responsibility**
```tsx
// bad
function RecordManager() {
  // data fetching + filtering + display + edit
}

// good: separate concerns
function RecordManager() {
  const { records } = useRecords();
  const filtered = useRecordFilters(records);
  return <RecordList records={filtered} />;
}
```

## component design

**keep components focused and maintainable**
```tsx
// bad: component doing too many things

// good: extract custom hooks and separate concerns
function Review() {
  const { pipelines } = usePipelines();
  const { records } = useRecords(pipelineId);
  const { currentIndex } = useNavigation();

  return (
    <Box>
      <ReviewHeader pipelines={pipelines} />
      <ReviewContent records={records} currentIndex={currentIndex} />
    </Box>
  );
}
```

**avoid prop drilling**
```tsx
// bad: 12 props passed
<SingleRecordView
  record={record}
  onNext={goNext}
  onPrevious={goPrevious}
  onAccept={() => updateStatus(id, "accepted")}
  onReject={() => updateStatus(id, "rejected")}
  onEdit={handleEdit}
  // ... 6 more props
/>

// good: use context for actions
function Review() {
  return (
    <RecordActionsProvider>
      <SingleRecordView record={record} currentIndex={index} />
    </RecordActionsProvider>
  );
}

function SingleRecordView({ record, currentIndex }: Props) {
  const { updateStatus } = useRecordActions();
  return <Button onClick={() => updateStatus(record.id, "accepted")}>Accept</Button>;
}
```

**extract reusable components**
```tsx
// bad: repeated jsx 6 times
<Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
  <Box as="kbd" sx={{ padding: "2px 6px", ... }}>A</Box>
  <Text>Accept</Text>
</Box>

// good: create component
function KeyboardShortcut({ shortcut, label }: Props) {
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
      <Box as="kbd" sx={{ padding: "2px 6px", ... }}>{shortcut}</Box>
      <Text>{label}</Text>
    </Box>
  );
}
```

**rules**:
- keep components reasonably sized (consider extracting if getting unwieldy)
- if copy-paste jsx more than twice, extract component
- prefer max 5 props per component (use context for more)

---

## state management

**group related state**
```tsx
// bad: scattered state
const [records, setRecords] = useState<RecordData[]>([]);
const [loading, setLoading] = useState(false);
const [error, setError] = useState<string | null>(null);
const [total, setTotal] = useState(0);
const [page, setPage] = useState(1);

// good: use reducer
interface RecordsState {
  data: RecordData[];
  loading: boolean;
  error: string | null;
  pagination: { total: number; page: number };
}

type Action =
  | { type: "FETCH_START" }
  | { type: "FETCH_SUCCESS"; payload: RecordData[]; total: number }
  | { type: "FETCH_ERROR"; error: string };

const [state, dispatch] = useReducer(recordsReducer, initialState);
```

**don't couple to localstorage**
```tsx
// bad: localStorage in component
const [viewMode, setViewMode] = useState(() => {
  const saved = localStorage.getItem("review_view_mode");
  return (saved as "single" | "table") || "table";
});

useEffect(() => {
  localStorage.setItem("review_view_mode", viewMode);
}, [viewMode]);

// good: create abstraction
function usePersistedState<T>(key: string, defaultValue: T) {
  const [value, setValue] = useState<T>(() => {
    try {
      const stored = localStorage.getItem(key);
      return stored ? JSON.parse(stored) : defaultValue;
    } catch {
      return defaultValue;
    }
  });

  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(value));
  }, [key, value]);

  return [value, setValue];
}

// usage
const [viewMode, setViewMode] = usePersistedState("review_view_mode", "table");
```

**rules**:
- use useState for simple state
- use useReducer when state becomes complex or related
- abstract localStorage access

---

## react hooks

**stable dependencies**
```tsx
// bad: unstable dependencies
const loadRecords = async () => { /* ... */ };

useEffect(() => {
  loadRecords();  // recreated every render!
}, [selectedPipeline]);

// good: useCallback
const loadRecords = useCallback(async () => {
  if (!selectedPipeline) return;
  const data = await api.getRecords({ pipelineId: selectedPipeline.id });
  setRecords(data);
}, [selectedPipeline]);

useEffect(() => {
  loadRecords();
}, [loadRecords]);  // stable reference
```

**always clean up**
```tsx
// bad: no cleanup
useEffect(() => {
  const interval = setInterval(() => {
    fetch("/api/status").then(handleStatus);
  }, 2000);
}, []);

// good: cleanup
useEffect(() => {
  let mounted = true;
  const controller = new AbortController();

  const poll = async () => {
    try {
      const res = await fetch("/api/status", { signal: controller.signal });
      const data = await res.json();
      if (mounted) setStatus(data);
    } catch (err) {
      if (err.name !== "AbortError") console.error(err);
    }
  };

  poll();
  const interval = setInterval(poll, 2000);

  return () => {
    mounted = false;
    controller.abort();
    clearInterval(interval);
  };
}, []);
```

**memoize expensive calculations**
```tsx
// bad: recalculate every render
function TableView({ records }: Props) {
  const finalState = getFinalState(record);  // runs every render!
  return <Table>...</Table>;
}

// good: use useMemo
function TableView({ records }: Props) {
  const finalState = useMemo(() => getFinalState(record), [record]);
  return <Table>...</Table>;
}
```

**rules**:
- use useCallback for stable function references
- always return cleanup from effects
- use useMemo for expensive calculations
- use AbortController for fetch calls

---

## api integration

**centralize api calls**
```tsx
// services/api.ts
class ApiClient {
  private baseUrl = "/api";

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: { "Content-Type": "application/json", ...options?.headers },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  async getPipelines(): Promise<Pipeline[]> {
    return this.request<Pipeline[]>("/pipelines");
  }

  async getRecords(filters: RecordFilters): Promise<RecordData[]> {
    const params = new URLSearchParams();
    if (filters.status) params.append("status", filters.status);
    return this.request<RecordData[]>(`/records?${params}`);
  }
}

export const api = new ApiClient();
```

**create custom hooks**
```tsx
// hooks/useApi.ts
function useApi<T>(apiCall: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiCall();
      setData(result);
    } catch (err) {
      const message = err instanceof Error ? err.message : "request failed";
      setError(message);
      console.error("api call failed:", err);
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  useEffect(() => { execute(); }, [execute]);

  return { data, loading, error, refetch: execute };
}

// usage
function Review() {
  const { data: pipelines, loading, error } = useApi(() => api.getPipelines());
  if (loading) return <Spinner />;
  if (error) return <Flash variant="danger">{error}</Flash>;
  return <PipelinesList pipelines={pipelines} />;
}
```

**rules**:
- centralize api logic in service module
- create custom hooks for common operations
- always handle loading and error states

---

## error handling

**never fail silently**
```tsx
// bad
try {
  await api.updateRecord(id, updates);
} catch {
  // user sees nothing!
}

// good
try {
  await api.updateRecord(id, updates);
  showToast({ type: "success", message: "record updated" });
} catch (err) {
  const message = err instanceof Error ? err.message : "failed to update";
  console.error("record update failed:", err);
  showToast({ type: "error", message });
}
```

**use error boundaries**
```tsx
class ErrorBoundary extends Component<Props, State> {
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <Box sx={{ p: 4, textAlign: "center" }}>
          <Heading>Something went wrong</Heading>
          <Button onClick={() => this.setState({ hasError: false })}>
            Try again
          </Button>
        </Box>
      );
    }
    return this.props.children;
  }
}
```

**rules**:
- never catch errors without logging
- show user feedback for failures
- use error boundaries for component errors

---

## typescript

**avoid `any` and type assertions**
```tsx
// bad
const data = await res.json() as any;
const value = localStorage.getItem("key") as string;  // can be null!

// good
interface ApiResponse {
  id: number;
  name: string;
}

const data: ApiResponse = await res.json();

const value = localStorage.getItem("key");
if (value === null) {
  // handle missing
}
```

**use type guards**
```tsx
// bad
function processRecord(record: Record | null) {
  const id = record!.id;  // unsafe!
}

// good
function processRecord(record: Record | null): number | null {
  if (record === null) return null;
  return record.id;  // typescript knows it's not null
}

// custom type guard
function isErrorResponse(response: ApiResponse): response is ErrorResponse {
  return "error" in response;
}
```

**rules**:
- no `any` types (use `unknown` if needed)
- no `as` type assertions (use type guards)
- all props have interfaces
- handle nullable values properly

---

## performance

**memoize expensive renders**
```tsx
// bad: re-renders on every parent change
function RecordCard({ record, onSelect }: Props) {
  return <Box onClick={() => onSelect(record.id)}>{record.name}</Box>;
}

// good: memo to prevent unnecessary re-renders
const RecordCard = memo(function RecordCard({ record, onSelect }: Props) {
  return <Box onClick={() => onSelect(record.id)}>{record.name}</Box>;
});
```

**stable callback references**
```tsx
// bad: new callback every render
function Parent() {
  return <Child onClick={(id) => console.log(id)} />;
}

// good: useCallback
function Parent() {
  const handleClick = useCallback((id: number) => {
    console.log(id);
  }, []);
  return <Child onClick={handleClick} />;
}
```

**lazy load heavy components**
```tsx
// bad: load everything upfront
import PipelineEditor from "./PipelineEditor";

// good: lazy load
const PipelineEditor = lazy(() => import("./PipelineEditor"));

function App() {
  return (
    <Suspense fallback={<Spinner />}>
      <PipelineEditor />
    </Suspense>
  );
}
```

**rules**:
- use React.memo for expensive components
- use useCallback for stable callbacks
- use useMemo for expensive calculations
- lazy load heavy components

---

## testing

**write testable code**
```tsx
// bad: untestable
function Review() {
  useEffect(() => {
    fetch("/api/records").then(res => res.json()).then(setRecords);
  }, []);
}

// good: testable
class RecordsAPI {
  async getRecords(): Promise<RecordData[]> {
    const res = await fetch("/api/records");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }
}

function useRecords() {
  const [records, setRecords] = useState<RecordData[]>([]);
  useEffect(() => {
    RecordsAPI.getRecords().then(setRecords);
  }, []);
  return records;
}

function Review() {
  const records = useRecords();
  return <RecordsList records={records} />;
}
```

**test user behavior**
```tsx
// bad: testing implementation
test("increments counter state", () => {
  const { result } = renderHook(() => useCounter());
  act(() => result.current.increment());
  expect(result.current.count).toBe(1);
});

// good: testing user behavior
test("shows incremented count when button clicked", () => {
  render(<Counter />);
  fireEvent.click(screen.getByRole("button", { name: /increment/i }));
  expect(screen.getByText("Count: 1")).toBeInTheDocument();
});
```

**rules**:
- extract business logic from components
- test user behavior, not implementation
- mock api calls in tests

---

## ui/ux quality

### theme compatibility
**always verify light and dark mode**
```tsx
// bad: hardcoded colors
<Text sx={{ color: "#000" }}>Title</Text>
<Box sx={{ backgroundColor: "#fff" }}>Content</Box>

// good: theme variables
<Text sx={{ color: "fg.default" }}>Title</Text>
<Box sx={{ backgroundColor: "canvas.default" }}>Content</Box>
```

**test in both modes before committing**
- toggle theme in app settings
- verify all text readable (fg.default, fg.muted, fg.subtle)
- verify backgrounds use canvas.* colors
- verify borders use border.default
- check interactive states (hover, focus, disabled)

**rules**:
- never hardcode colors (#000, #fff, rgb(), etc.)
- always use primer theme variables
- test every UI change in both light and dark mode
- if text looks wrong, it probably needs fg.* color

---

## checklist

before committing, verify:

**components**
- [ ] component reasonably sized
- [ ] single responsibility
- [ ] prefer max 5 props (use context if needed)

**state**
- [ ] related state grouped
- [ ] complex state uses useReducer
- [ ] no direct localStorage access

**hooks**
- [ ] stable dependencies (useCallback)
- [ ] cleanup function returns
- [ ] AbortController for fetch
- [ ] mounted flag for async

**api**
- [ ] api calls through service layer
- [ ] custom hooks for data fetching
- [ ] error handling with user feedback
- [ ] loading states shown

**error handling**
- [ ] no silent failures
- [ ] errors logged
- [ ] user feedback for failures
- [ ] error boundaries

**typescript**
- [ ] no `any` types
- [ ] no `as` assertions
- [ ] all props have interfaces
- [ ] nullable values handled

**performance**
- [ ] expensive calcs use useMemo
- [ ] callbacks use useCallback
- [ ] components memoized where needed
- [ ] heavy components lazy loaded

**testing**
- [ ] business logic extracted
- [ ] api calls mockable
- [ ] tests for new features

**ui/ux**
- [ ] theme compatibility verified in both light and dark modes
- [ ] no hardcoded colors (use theme variables)

---

**golden rule**: keep components focused and maintainable. refactor when complexity becomes unwieldy.
